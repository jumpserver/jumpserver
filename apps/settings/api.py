# -*- coding: utf-8 -*-
#

import os
import json
import jms_storage

from rest_framework.views import Response, APIView
from rest_framework.generics import GenericAPIView
from ldap3 import Server, Connection
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _
from common.permissions import IsOrgAdmin, IsSuperUser
from settings.utils import (ldap_conn, ldap_bind, ldap_search,
                            get_ldap_setting, save_user)
from .serializers import (MailTestSerializer, LDAPTestSerializer)
from .models import Setting, settings


class MailTestingAPI(APIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = MailTestSerializer
    success_message = _("Test mail sent to {}, please check")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email_host_user = serializer.validated_data["EMAIL_HOST_USER"]
            for k, v in serializer.validated_data.items():
                if k.startswith('EMAIL'):
                    setattr(settings, k, v)
            try:
                subject = "Test"
                message = "Test smtp setting"
                send_mail(subject, message,  email_host_user, [email_host_user])
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            return Response({"msg": self.success_message.format(email_host_user)})
        else:
            return Response({"error": str(serializer.errors)}, status=401)


class LDAPTestingAPI(APIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = LDAPTestSerializer
    success_message = _("Test ldap success")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            host = serializer.validated_data["AUTH_LDAP_SERVER_URI"]
            bind_dn = serializer.validated_data["AUTH_LDAP_BIND_DN"]
            password = serializer.validated_data["AUTH_LDAP_BIND_PASSWORD"]
            use_ssl = serializer.validated_data.get("AUTH_LDAP_START_TLS", False)
            search_ougroup = serializer.validated_data["AUTH_LDAP_SEARCH_OU"]
            search_filter = serializer.validated_data["AUTH_LDAP_SEARCH_FILTER"]
            attr_map = serializer.validated_data["AUTH_LDAP_USER_ATTR_MAP"]

            try:
                attr_map = json.loads(attr_map)
            except json.JSONDecodeError:
                return Response({"error": "AUTH_LDAP_USER_ATTR_MAP not valid"}, status=401)

            server = Server(host, use_ssl=use_ssl)
            conn = Connection(server, bind_dn, password)
            try:
                conn.bind()
            except Exception as e:
                return Response({"error": str(e)}, status=401)

            users = []
            for search_ou in str(search_ougroup).split("|"):
                ok = conn.search(search_ou, search_filter % ({"user": "*"}),
                                 attributes=list(attr_map.values()))
                if not ok:
                    return Response({"error": _("Search no entry matched in ou {}").format(search_ou)}, status=401)

                for entry in conn.entries:
                    user = {}
                    for attr, mapping in attr_map.items():
                        if hasattr(entry, mapping):
                            user[attr] = getattr(entry, mapping)
                    users.append(user)
            if len(users) > 0:
                return Response({"msg": _("Match {} s users").format(len(users))})
            else:
                return Response({"error": "Have user but attr mapping error"}, status=401)
        else:
            return Response({"error": str(serializer.errors)}, status=401)


class LDAPSyncAPI(GenericAPIView):
    permission_classes = (IsOrgAdmin,)

    def get(self, request):
        ldap_setting = get_ldap_setting()
        if type(ldap_setting) != dict:
            return ldap_setting

        conn = ldap_conn(ldap_setting['host'], ldap_setting['use_ssl'],
                         ldap_setting['bind_dn'], ldap_setting['password'])

        ldap_bind(conn)

        result_search = ldap_search(conn, ldap_setting['search_ougroup'],
                                    ldap_setting['search_filter'],
                                    ldap_setting['attr_map'])

        if type(result_search) != list:
            return Response(result_search, status=401)
        return Response(result_search)


class LDAPConfirmSyncAPI(APIView):
    permission_classes = (IsOrgAdmin,)

    def get(self, request):

        user_names = request.GET.getlist('user_names', '')
        if not user_names:
            return Response({'error': _('当前无选择用户，请勾选需要导入的用户')}, status=401)
        ldap_setting = get_ldap_setting()

        conn = ldap_conn(ldap_setting['host'], ldap_setting['use_ssl'],
                         ldap_setting['bind_dn'], ldap_setting['password'])

        ldap_bind(conn)
        result_search = ldap_search(conn, ldap_setting['search_ougroup'],
                                    ldap_setting['search_filter'],
                                    ldap_setting['attr_map'],
                                    user_names=user_names)

        if type(result_search) != list:
            return Response(result_search, status=401)

        result = save_user(result_search)
        return result


class ReplayStorageCreateAPI(APIView):
    permission_classes = (IsSuperUser,)

    def post(self, request):
        storage_data = request.data

        if storage_data.get('TYPE') == 'ceph':
            port = storage_data.get('PORT')
            if port.isdigit():
                storage_data['PORT'] = int(storage_data.get('PORT'))

        storage_name = storage_data.pop('NAME')
        data = {storage_name: storage_data}

        if not self.is_valid(storage_data):
            return Response({
                "error": _("Error: Account invalid (Please make sure the "
                           "information such as Access key or Secret key is correct)")},
                status=401
            )

        Setting.save_storage('TERMINAL_REPLAY_STORAGE', data)
        return Response({"msg": _('Create succeed')}, status=200)

    @staticmethod
    def is_valid(storage_data):
        if storage_data.get('TYPE') == 'server':
            return True
        storage = jms_storage.get_object_storage(storage_data)
        target = 'tests.py'
        src = os.path.join(settings.BASE_DIR, 'common', target)
        return storage.is_valid(src, target)


class ReplayStorageDeleteAPI(APIView):
    permission_classes = (IsSuperUser,)

    def post(self, request):
        storage_name = str(request.data.get('name'))
        Setting.delete_storage('TERMINAL_REPLAY_STORAGE', storage_name)
        return Response({"msg": _('Delete succeed')}, status=200)


class CommandStorageCreateAPI(APIView):
    permission_classes = (IsSuperUser,)

    def post(self, request):
        storage_data = request.data
        storage_name = storage_data.pop('NAME')
        data = {storage_name: storage_data}
        if not self.is_valid(storage_data):
            return Response(
                {"error": _("Error: Account invalid (Please make sure the "
                            "information such as Access key or Secret key is correct)")},
                status=401
            )

        Setting.save_storage('TERMINAL_COMMAND_STORAGE', data)
        return Response({"msg": _('Create succeed')}, status=200)

    @staticmethod
    def is_valid(storage_data):
        if storage_data.get('TYPE') == 'server':
            return True
        try:
            storage = jms_storage.get_log_storage(storage_data)
        except Exception:
            return False

        return storage.ping()


class CommandStorageDeleteAPI(APIView):
    permission_classes = (IsSuperUser,)

    def post(self, request):
        storage_name = str(request.data.get('name'))
        Setting.delete_storage('TERMINAL_COMMAND_STORAGE', storage_name)
        return Response({"msg": _('Delete succeed')}, status=200)


class DjangoSettingsAPI(APIView):
    def get(self, request):
        if not settings.DEBUG:
            return Response("Not in debug mode")

        data = {}
        for i in [settings, getattr(settings, '_wrapped')]:
            if not i:
                continue
            for k, v in i.__dict__.items():
                if k and k.isupper():
                    try:
                        json.dumps(v)
                        data[k] = v
                    except (json.JSONDecodeError, TypeError):
                        data[k] = str(v)
        return Response(data)



