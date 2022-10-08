from django.db.models import F, Value
from django.db.models.functions import Concat
from django_filters.rest_framework import CharFilter
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema

from orgs.utils import current_org
from common.drf.filters import BaseFilterSet

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

#
# class CommandExecutionFilter(BaseFilterSet):
#     hostname_ip = CharFilter(method='filter_hostname_ip')
#
#     class Meta:
#         model = CommandExecution.hosts.through
#         fields = (
#             'id', 'asset', 'commandexecution', 'hostname_ip'
#         )
#
#     def filter_hostname_ip(self, queryset, name, value):
#         queryset = queryset.annotate(
#             hostname_ip=Concat(
#                 F('asset__hostname'), Value('('),
#                 F('asset__address'), Value(')')
#             )
#         ).filter(hostname_ip__icontains=value)
#         return queryset
