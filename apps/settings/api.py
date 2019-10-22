# -*- coding: utf-8 -*-
#

import os
import json
import jms_storage

from smtplib import SMTPSenderRefused
from rest_framework import generics
from rest_framework.views import Response, APIView
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import ugettext_lazy as _

from .models import Setting
from .utils import LDAPUtil
from common.permissions import IsOrgAdmin, IsSuperUser
from common.utils import get_logger
from .serializers import MailTestSerializer, LDAPTestSerializer, LDAPUserSerializer


logger = get_logger(__file__)


class MailTestingAPI(APIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = MailTestSerializer
    success_message = _("Test mail sent to {}, please check")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email_from = serializer.validated_data["EMAIL_FROM"]
            email_recipient = serializer.validated_data["EMAIL_RECIPIENT"]
            email_host_user = serializer.validated_data["EMAIL_HOST_USER"]
            for k, v in serializer.validated_data.items():
                if k.startswith('EMAIL'):
                    setattr(settings, k, v)
            try:
                subject = "Test"
                message = "Test smtp setting"
                email_from = email_from or email_host_user
                email_recipient = email_recipient or email_from
                send_mail(subject, message,  email_from, [email_recipient])
            except SMTPSenderRefused as e:
                resp = e.smtp_error
                if isinstance(resp, bytes):
                    for coding in ('gbk', 'utf8'):
                        try:
                            resp = resp.decode(coding)
                        except UnicodeDecodeError:
                            continue
                        else:
                            break
                return Response({"error": str(resp)}, status=401)
            except Exception as e:
                print(e)
                return Response({"error": str(e)}, status=401)
            return Response({"msg": self.success_message.format(email_recipient)})
        else:
            return Response({"error": str(serializer.errors)}, status=401)


class LDAPTestingAPI(APIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = LDAPTestSerializer
    success_message = _("Test ldap success")

    @staticmethod
    def get_ldap_util(serializer):
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

        util = LDAPUtil(
            use_settings_config=False, server_uri=host, bind_dn=bind_dn,
            password=password, use_ssl=use_ssl,
            search_ougroup=search_ougroup, search_filter=search_filter,
            attr_map=attr_map
        )
        return util

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response({"error": str(serializer.errors)}, status=401)

        util = self.get_ldap_util(serializer)

        try:
            users = util.search_user_items()
        except Exception as e:
            return Response({"error": str(e)}, status=401)

        if len(users) > 0:
            return Response({"msg": _("Match {} s users").format(len(users))})
        else:
            return Response({"error": "Have user but attr mapping error"}, status=401)


class LDAPUserListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = LDAPUserSerializer

    def get_queryset(self):
        if hasattr(self, 'swagger_fake_view'):
            return []
        q = self.request.query_params.get('search')
        try:
            util = LDAPUtil()
            extra_filter = util.construct_extra_filter(util.SEARCH_FIELD_ALL, q)
            users = util.search_user_items(extra_filter)
        except Exception as e:
            users = []
            logger.error(e)
        # 前端data_table会根据row.id对table.selected值进行操作
        for user in users:
            user['id'] = user['username']
        return users

    def sort_queryset(self, queryset):
        order_by = self.request.query_params.get('order')
        if not order_by:
            order_by = 'existing'
        if order_by.startswith('-'):
            order_by = order_by.lstrip('-')
            reverse = True
        else:
            reverse = False
        queryset = sorted(queryset, key=lambda x: x[order_by], reverse=reverse)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset = self.sort_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(queryset)


class LDAPUserSyncAPI(APIView):
    permission_classes = (IsOrgAdmin,)

    def post(self, request):
        username_list = request.data.get('username_list', [])

        util = LDAPUtil()
        try:
            result = util.sync_users(username_list)
        except Exception as e:
            logger.error(e, exc_info=True)
            return Response({'error': str(e)}, status=401)
        else:
            msg = _("succeed: {} failed: {} total: {}").format(
                result['succeed'], result['failed'], result['total']
            )
            return Response({'msg': msg})


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
