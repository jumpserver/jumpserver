# -*- coding: utf-8 -*-

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import generics

from common.exceptions import JMSException
from common.utils import get_logger
from users.models import User
from ..models import Setting
from ..serializers import LDAPUserQuerySerializer, LDAPUserSerializer
from ..utils import (
    LDAPServerUtil, LDAPCacheUtil,
    LDAP_USE_CACHE_FLAGS
)

logger = get_logger(__file__)


@extend_schema(parameters=[LDAPUserQuerySerializer])
class LDAPUserListApi(generics.ListAPIView):
    serializer_class = LDAPUserSerializer
    perm_model = Setting
    rbac_perms = {
        'list': 'settings.change_auth'
    }

    def get_queryset(self):
        if hasattr(self, 'swagger_fake_view'):
            return User.objects.none()

        # Keep explicit empty values from being treated as omitted HTML fields.
        query = LDAPUserQuerySerializer(data=self.request.query_params.dict())
        query.is_valid(raise_exception=True)
        category = query.validated_data['category']
        server_uri = getattr(settings, f'AUTH_{category.upper()}_SERVER_URI')
        if not (server_uri or '').strip():
            raise JMSException(
                code='ldap_not_configured',
                detail=_('LDAP server is not configured. Please configure it in Authentication settings.'),
            )

        cache_police = self.request.query_params.get('cache_police', True)
        util_class = LDAPCacheUtil if cache_police in LDAP_USE_CACHE_FLAGS else LDAPServerUtil
        try:
            users = util_class(category=category).search(search_value=self.request.query_params.get('search'))
        except Exception as exc:
            logger.exception('Failed to query %s users', category)
            raise JMSException(
                code='ldap_query_failed',
                detail=_('Unable to load LDAP users. Please try again later or contact the administrator.'),
            ) from exc

        if users is None:
            raise JMSException(
                code='ldap_users_not_synchronized',
                detail=_('Users are not synchronized, please click the user synchronization button'),
            )
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
        queryset = sorted(queryset, key=lambda x: x.get(order_by, ''), reverse=reverse)
        return queryset

    def filter_queryset(self, queryset):
        if queryset is None:
            return queryset
        queryset = self.processing_queryset(queryset)
        queryset = self.sort_queryset(queryset)
        return queryset
