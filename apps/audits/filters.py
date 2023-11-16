from django.core.cache import cache
from django_filters import rest_framework as drf_filters
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema

from common.drf.filters import BaseFilterSet
from notifications.ws import WS_SESSION_KEY
from orgs.utils import current_org
from .models import UserSession

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
        redis_client = cache.client.get_client()
        members = redis_client.smembers(WS_SESSION_KEY)
        members = [member.decode('utf-8') for member in members]
        if is_active:
            queryset = queryset.filter(key__in=members)
        else:
            queryset = queryset.exclude(key__in=members)
        return queryset

    class Meta:
        model = UserSession
        fields = ['id', 'ip', 'city', 'type']
