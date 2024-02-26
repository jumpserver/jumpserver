from django.apps import apps
from django.utils import translation

from django_filters import rest_framework as drf_filters
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema
from common.drf.filters import BaseFilterSet
from common.sessions.cache import user_session_manager
from orgs.utils import current_org
from .models import UserSession, OperateLog

__all__ = ['CurrentOrgMembersFilter']


class CurrentOrgMembersFilter(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='user', location='query', required=False, type='string',
                schema=coreschema.String(
                    title='user',
                    description='user'
                )
            )
        ]

    def _get_user_list(self):
        users = current_org.get_members(exclude=('Auditor',))
        return users

    def filter_queryset(self, request, queryset, view):
        user_id = request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user=user_id)
        else:
            queryset = queryset.filter(user__in=self._get_user_list())
        return queryset


class UserSessionFilterSet(BaseFilterSet):
    is_active = drf_filters.BooleanFilter(method='filter_is_active')

    @staticmethod
    def filter_is_active(queryset, name, is_active):
        keys = user_session_manager.get_active_keys()
        if is_active:
            queryset = queryset.filter(key__in=keys)
        else:
            queryset = queryset.exclude(key__in=keys)
        return queryset

    class Meta:
        model = UserSession
        fields = ['id', 'ip', 'city', 'type']


class OperateLogFilterSet(BaseFilterSet):
    resource_type = drf_filters.CharFilter(method='filter_resource_type')

    @staticmethod
    def filter_resource_type(queryset, name, resource_type):
        current_lang = translation.get_language()
        with translation.override(current_lang):
            mapper = {str(m._meta.verbose_name): m._meta.verbose_name_raw for m in apps.get_models()}
        tp = mapper.get(resource_type)
        queryset = queryset.filter(resource_type=tp)
        return queryset

    class Meta:
        model = OperateLog
        fields = [
            'user', 'action', 'resource', 'remote_addr'
        ]
