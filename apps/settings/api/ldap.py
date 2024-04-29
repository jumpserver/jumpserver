# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _
from rest_framework import generics
from rest_framework.views import Response

from common.utils import get_logger
from users.models import User
from ..models import Setting
from ..serializers import LDAPUserSerializer
from ..utils import (
    LDAPServerUtil, LDAPCacheUtil,
    LDAP_USE_CACHE_FLAGS
)

logger = get_logger(__file__)


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
        else:
            data = {'msg': _('Users are not synchronized, please click the user synchronization button')}
            return Response(data=data, status=400)
