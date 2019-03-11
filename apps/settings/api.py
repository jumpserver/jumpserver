# -*- coding: utf-8 -*-
#

import os
import json
import jms_storage
from django.db.models import Q

from rest_framework.views import Response, APIView
from rest_framework.generics import GenericAPIView
from ldap3 import Server, Connection
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _

from common.permissions import IsOrgAdmin, IsSuperUser
from .serializers import (
    MailTestSerializer, LDAPTestSerializer
)
from .models import Setting
from .models import settings
from users.models import User


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


def get_ldap_setting():
    host = settings.AUTH_LDAP_SERVER_URI
    bind_dn = settings.AUTH_LDAP_BIND_DN
    password = settings.AUTH_LDAP_BIND_PASSWORD
    use_ssl = settings.AUTH_LDAP_START_TLS
    search_ougroup = settings.AUTH_LDAP_SEARCH_OU
    search_filter = settings.AUTH_LDAP_SEARCH_FILTER
    attr_map = settings.AUTH_LDAP_USER_ATTR_MAP
    auth_ldap = settings.AUTH_LDAP

    if not host:
        return Response({'error': _("请设置Ldap站点地址并提交")}, status=401)
    if not password:
        return Response({'error': _("请设置Ldap密码并提交")}, status=401)
    if not bind_dn:
        return Response({'error': _("请设置Ldap的DN并提交")}, status=401)
    if not search_ougroup:
        return Response({'error': _("请设置Ldap的用户OU并提交")}, status=401)
    if not search_filter:
        return Response({'error': _("请先设置Ldap用户过滤器并提交")}, status=401)
    if not attr_map:
        return Response({'error': _("请先设置Ldap属性映射并提交")}, status=401)
    if not auth_ldap:
        return Response({'error': _("请先勾选启用LDAP认证")}, status=401)

    ldap_setting = {
        'host': host, 'bind_dn':bind_dn, 'password': password,
        'search_ougroup': search_ougroup, 'search_filter': search_filter,
        'attr_map': attr_map, 'auth_ldap': auth_ldap, 'use_ssl': use_ssl,
    }
    return ldap_setting


def save_user(users):
    if len(users) > 0:
        exist = []
        for item in users:
            if not item.get('email', ''):
                item['email'] = item['username'] + '@' + item[
                    'username'] + '.com'
            item['source'] = 'ldap'
            user = User.objects.filter(
                Q(username=item['username']) & ~Q(source='ldap'))
            if user:
                exist.append(item['username'])
                continue
            user = User.objects.filter(username=item['username'], source='ldap')
            if user:
                user = user[0]
                user.username = item.get('username', '')
                user.name = item.get('name', '')
                user.email = item['email']
                user.source = item['source']
                user.save()
            else:
                try:
                    user = User.objects.create(**item)
                except:

                    exist.append(item['username'])
                    continue
        if exist:
            msg = _("导入 {} 个用户成功, 导入 {} 这些用户失败，数据库已经存在同名的用户")\
                .format(len(users) - len(exist), str(exist))
        else:
            msg = _("导入 {} 个用户成功").format(len(users))
        return Response(
            {"msg": msg})
    else:
        return Response({"error": "Have user but attr mapping error"},
                        status=401)


class LDAPSyncAPI(GenericAPIView):
    permission_classes = (IsOrgAdmin,)

    def get(self, request):

        ldap_setting = get_ldap_setting()
        if type(ldap_setting) != dict:
            return ldap_setting

        server = Server(ldap_setting['host'], use_ssl=ldap_setting['use_ssl'])
        conn = Connection(server, ldap_setting['bind_dn'], ldap_setting['password'])
        try:
            conn.bind()

        except Exception as e:
            return Response({"error": str(e)}, status=401)

        users = []
        for search_ou in str(ldap_setting['search_ougroup']).split("|"):
            ok = conn.search(search_ou, ldap_setting['search_filter'] % ({"user": "*"}),
                             attributes=list(ldap_setting['attr_map'].values()))
            if not ok:
                return Response({"error": _(
                    "Search no entry matched in ou {}").format(search_ou)},
                                status=401)

            for entry in conn.entries:
                user = {}
                for attr, mapping in ldap_setting['attr_map'].items():
                    if hasattr(entry, mapping):
                        user[attr] = getattr(entry, mapping).value if \
                            getattr(entry, mapping).value else ''
                users.append(user)
        if len(users) > 0:
            return Response(users)
        else:
            return Response({"error": "Have user but attr mapping error"},
                            status=401)


class LDAPConfirmSyncAPI(APIView):
    permission_classes = (IsOrgAdmin,)

    def get(self, request):

        user_names = request.GET.getlist('user_names', '')
        ldap_setting = get_ldap_setting()

        server = Server(ldap_setting['host'], use_ssl=ldap_setting['use_ssl'])
        conn = Connection(server, ldap_setting['bind_dn'],
                          ldap_setting['password'])
        try:
            conn.bind()
        except Exception as e:
            return Response({"error": str(e)}, status=401)

        users = []
        for search_ou in str(ldap_setting['search_ougroup']).split("|"):
            ok = conn.search(search_ou,
                             ldap_setting['search_filter'] % ({"user": "*"}),
                             attributes=list(ldap_setting['attr_map'].values()))
            if not ok:
                return Response({"error": _(
                    "Search no entry matched in ou {}").format(search_ou)},
                                status=401)

            for entry in conn.entries:
                user = {}
                for attr, mapping in ldap_setting['attr_map'].items():
                    if hasattr(entry, mapping):
                        user[attr] = getattr(entry, mapping).value if \
                            getattr(entry, mapping).value else ''

                if user.get('username', '') in user_names:
                    users.append(user)
        response = save_user(users)

        return response
        # if len(users) > 0:
        #     exist=[]
        #     for item in users:
        #         if not item.get('email', ''):
        #             item['email'] = item['username'] + '@' + item[
        #                 'username'] + '.com'
        #         item['source'] = 'ldap'
        #         user = User.objects.filter(Q(username=item['username']) & ~Q(source='ldap') )
        #         if user:
        #             # exist.append(item['username'])
        #             continue
        #         user = User.objects.filter(username=item['username'], source='ldap')
        #         if user:
        #             user = user[0]
        #             user.username = item.get('username', '')
        #             user.name = item.get('name', '')
        #             user.email = item['email']
        #             user.source = item['source']
        #             user.save()
        #         else:
        #             try:
        #                 user = User.objects.create(**item)
        #             except:
        #
        #                 exist.append(item['username'])
        #                 continue
        #
        #     return Response(
        #         {"msg": _("导入 {} 个用户成功, 导入 {} 这些用户失败，数据库已经存在同名的用户")
        #             .format(len(users)-len(exist), str(exist))})
        # else:
        #     return Response({"error": "Have user but attr mapping error"},
        #                     status=401)


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



