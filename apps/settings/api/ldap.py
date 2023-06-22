# -*- coding: utf-8 -*-
#

import threading

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import generics
from rest_framework.generics import CreateAPIView
from rest_framework.views import Response, APIView

from common.api import AsyncApiMixin
from common.utils import get_logger
from orgs.models import Organization
from orgs.utils import current_org
from users.models import User
from ..models import Setting
from ..serializers import (
    LDAPTestConfigSerializer, LDAPUserSerializer,
    LDAPTestLoginSerializer
)
from ..tasks import sync_ldap_user
from ..utils import (
    LDAPServerUtil, LDAPCacheUtil, LDAPImportUtil, LDAPSyncUtil,
    LDAP_USE_CACHE_FLAGS, LDAPTestUtil
)

logger = get_logger(__file__)


class LDAPTestingConfigAPI(AsyncApiMixin, CreateAPIView):
    serializer_class = LDAPTestConfigSerializer
    perm_model = Setting
    rbac_perms = {
        'POST': 'settings.change_auth',
        'create': 'settings.change_auth',
    }

    def is_need_async(self):
        return True

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response({"error": str(serializer.errors)}, status=400)
        config = self.get_ldap_config(serializer)
        ok, msg = LDAPTestUtil(config).test_config()
        status = 200 if ok else 400
        return Response(msg, status=status)

    @staticmethod
    def get_ldap_config(serializer):
        server_uri = serializer.validated_data["AUTH_LDAP_SERVER_URI"]
        bind_dn = serializer.validated_data["AUTH_LDAP_BIND_DN"]
        password = serializer.validated_data["AUTH_LDAP_BIND_PASSWORD"]
        use_ssl = serializer.validated_data.get("AUTH_LDAP_START_TLS", False)
        search_ou = serializer.validated_data["AUTH_LDAP_SEARCH_OU"]
        search_filter = serializer.validated_data["AUTH_LDAP_SEARCH_FILTER"]
        attr_map = serializer.validated_data["AUTH_LDAP_USER_ATTR_MAP"]
        auth_ldap = serializer.validated_data.get('AUTH_LDAP', False)

        if not password:
            password = settings.AUTH_LDAP_BIND_PASSWORD

        config = {
            'server_uri': server_uri,
            'bind_dn': bind_dn,
            'password': password,
            'use_ssl': use_ssl,
            'search_ou': search_ou,
            'search_filter': search_filter,
            'attr_map': attr_map,
            'auth_ldap': auth_ldap
        }
        return config


class LDAPTestingLoginAPI(APIView):
    serializer_class = LDAPTestLoginSerializer
    perm_model = Setting
    rbac_perms = {
        'POST': 'settings.change_auth'
    }

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response({"error": str(serializer.errors)}, status=400)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        ok, msg = LDAPTestUtil().test_login(username, password)
        status = 200 if ok else 400
        return Response(msg, status=status)


class LDAPUserListApi(generics.ListAPIView):
    serializer_class = LDAPUserSerializer
    perm_model = Setting
    rbac_perms = {
        'list': 'settings.change_auth'
    }

    def get_queryset_from_cache(self):
        search_value = self.request.query_params.get('search')
        users = LDAPCacheUtil().search(search_value=search_value)
        return users

    def get_queryset_from_server(self):
        search_value = self.request.query_params.get('search')
        users = LDAPServerUtil().search(search_value=search_value)
        return users

    def get_queryset(self):
        if hasattr(self, 'swagger_fake_view'):
            return User.objects.none()
        cache_police = self.request.query_params.get('cache_police', True)
        if cache_police in LDAP_USE_CACHE_FLAGS:
            users = self.get_queryset_from_cache()
        else:
            users = self.get_queryset_from_server()
        return users

    @staticmethod
    def processing_queryset(queryset):
        db_username_list = User.objects.all().values_list('username', flat=True)
        for q in queryset:
            q['id'] = q['username']
            q['existing'] = q['username'] in db_username_list
        return queryset

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

    def filter_queryset(self, queryset):
        if queryset is None:
            return queryset
        queryset = self.processing_queryset(queryset)
        queryset = self.sort_queryset(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        cache_police = self.request.query_params.get('cache_police', True)
        # 不是用缓存
        if cache_police not in LDAP_USE_CACHE_FLAGS:
            return super().list(request, *args, **kwargs)

        try:
            queryset = self.get_queryset()
        except Exception as e:
            data = {'error': str(e)}
            return Response(data=data, status=400)

        # 缓存有数据
        if queryset is not None:
            return super().list(request, *args, **kwargs)

        sync_util = LDAPSyncUtil()
        # 还没有同步任务
        if sync_util.task_no_start:
            ok, msg = LDAPTestUtil().test_config()
            if not ok:
                return Response(data={'msg': msg}, status=400)
            # 任务外部设置 task running 状态
            sync_util.set_task_status(sync_util.TASK_STATUS_IS_RUNNING)
            t = threading.Thread(target=sync_ldap_user)
            t.start()
            data = {'msg': _('Synchronization start, please wait.')}
            return Response(data=data, status=409)
        # 同步任务正在执行
        if sync_util.task_is_running:
            data = {'msg': _('Synchronization is running, please wait.')}
            return Response(data=data, status=409)
        # 同步任务执行结束
        if sync_util.task_is_over:
            msg = sync_util.get_task_error_msg()
            data = {'error': _('Synchronization error: {}'.format(msg))}
            return Response(data=data, status=400)

        return super().list(request, *args, **kwargs)


class LDAPUserImportAPI(APIView):
    perm_model = Setting
    rbac_perms = {
        'POST': 'settings.change_auth'
    }

    def get_orgs(self):
        org_ids = self.request.data.get('org_ids')
        if org_ids:
            orgs = list(Organization.objects.filter(id__in=org_ids))
        else:
            orgs = [current_org]
        return orgs

    def get_ldap_users(self):
        username_list = self.request.data.get('username_list', [])
        cache_police = self.request.query_params.get('cache_police', True)
        if '*' in username_list:
            users = LDAPServerUtil().search()
        elif cache_police in LDAP_USE_CACHE_FLAGS:
            users = LDAPCacheUtil().search(search_users=username_list)
        else:
            users = LDAPServerUtil().search(search_users=username_list)
        return users

    def post(self, request):
        try:
            users = self.get_ldap_users()
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        if users is None:
            return Response({'msg': _('Get ldap users is None')}, status=400)

        orgs = self.get_orgs()
        errors = LDAPImportUtil().perform_import(users, orgs)
        if errors:
            return Response({'errors': errors}, status=400)

        count = users if users is None else len(users)
        orgs_name = ', '.join([str(org) for org in orgs])
        return Response({
            'msg': _('Imported {} users successfully (Organization: {})').format(count, orgs_name)
        })


class LDAPCacheRefreshAPI(generics.RetrieveAPIView):
    perm_model = Setting
    rbac_perms = {
        'retrieve': 'settings.change_auth'
    }

    def retrieve(self, request, *args, **kwargs):
        try:
            LDAPSyncUtil().clear_cache()
        except Exception as e:
            logger.error(str(e))
            return Response(data={'msg': str(e)}, status=400)
        return Response(data={'msg': 'success'})
