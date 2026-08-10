from django.apps import apps
from django.db.models import Q
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as drf_filters
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema
from common.drf.filters import BaseFilterSet
from common.sessions.cache import user_session_manager
from common.utils import is_uuid
from ops.const import JobStatus
from ops.models import Job
from orgs.utils import current_org
from .auth_backends import get_auth_backend_choices
from .const import LoginTypeChoices, MFAChoices
from .models import (
    FTPLog, IntegrationApplicationLog, JobLog, OperateLog,
    PasswordChangeLog, UserLoginLog, UserSession,
)

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
    user = drf_filters.CharFilter(
        method='filter_user', label=_('User name, username or ID')
    )
    is_active = drf_filters.BooleanFilter(
        method='filter_is_active', label=_('Is active')
    )
    type = drf_filters.ChoiceFilter(
        choices=LoginTypeChoices.choices, label=_('Login type')
    )
    backend = drf_filters.ChoiceFilter(
        choices=get_auth_backend_choices(), label=_('Auth backend')
    )

    @staticmethod
    def filter_user(queryset, name, value):
        query = (
            Q(user__name__icontains=value) |
            Q(user__username__icontains=value)
        )
        if is_uuid(value):
            query |= Q(user_id=value)
        return queryset.filter(query)

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
        fields = [
            'id', 'user', 'ip', 'city', 'type', 'backend',
            'user_agent', 'is_active',
        ]
        fields_operator = {
            'user': ('icontains',),
            'ip': ('exact', 'in'),
        }


class FTPLogFilterSet(BaseFilterSet):
    user = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('User name')
    )
    asset = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('Asset name')
    )
    account = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('Account name')
    )
    remote_addr = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('Remote address')
    )
    session = drf_filters.CharFilter(
        lookup_expr='exact', label=_('Session ID')
    )

    class Meta:
        model = FTPLog
        fields = [
            'id', 'user', 'asset', 'account', 'filename', 'remote_addr',
            'operate', 'is_success', 'session',
        ]
        fields_operator = {
            'session': ('exact', 'in'),
        }


class UserLoginLogFilterSet(BaseFilterSet):
    type = drf_filters.ChoiceFilter(
        choices=LoginTypeChoices.choices, label=_('Login type')
    )
    status = drf_filters.BooleanFilter(label=_('Status'))
    mfa = drf_filters.ChoiceFilter(
        choices=MFAChoices.choices, label=_('MFA')
    )
    backend = drf_filters.ChoiceFilter(
        choices=get_auth_backend_choices(), label=_('Auth backend')
    )

    class Meta:
        model = UserLoginLog
        fields = [
            'id', 'username', 'ip', 'city', 'type', 'backend',
            'status', 'mfa', 'user_agent',
        ]
        fields_operator = {
            'ip': ('exact', 'in'),
        }


class PasswordChangeLogFilterSet(BaseFilterSet):
    user = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('User name')
    )
    change_by = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('Change by')
    )
    remote_addr = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('Remote address')
    )

    class Meta:
        model = PasswordChangeLog
        fields = ['id', 'user', 'change_by', 'remote_addr']


class OperateLogFilterSet(BaseFilterSet):
    user = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('User name')
    )
    remote_addr = drf_filters.CharFilter(
        lookup_expr='iexact', label=_('Remote address')
    )
    resource_type = drf_filters.CharFilter(
        method='filter_resource_type', label=_('Resource type')
    )

    @staticmethod
    def filter_resource_type(queryset, name, resource_type):
        current_lang = translation.get_language()
        with translation.override(current_lang):
            mapper = {str(m._meta.verbose_name): m._meta.verbose_name_raw for m in apps.get_models()}
        tp = mapper.get(resource_type)
        queryset = queryset.filter(resource_type__in=[tp, resource_type])
        return queryset

    class Meta:
        model = OperateLog
        fields = [
            'id', 'user', 'action', 'resource_type', 'resource',
            'remote_addr',
        ]
        fields_operator = {
            'resource_type': ('exact',),
        }


class ServiceAccessLogFilterSet(BaseFilterSet):
    service_id = drf_filters.UUIDFilter(label=_("Application ID"))

    class Meta:
        model = IntegrationApplicationLog
        fields = [
            "id", "service", "service_id", "asset", "account",
            "remote_addr",
        ]


class JobLogFilterSet(BaseFilterSet):
    creator__name = drf_filters.CharFilter(
        field_name="creator__name", label=_("Creator name")
    )
    status = drf_filters.ChoiceFilter(
        choices=JobStatus.choices, label=_("Status")
    )
    task_id = drf_filters.UUIDFilter(label=_("Task ID"))

    class Meta:
        model = JobLog
        fields = [
            "id", "material", "job_type", "status",
            "task_id", "creator__name",
        ]


class JobsAuditFilterSet(BaseFilterSet):
    creator__name = drf_filters.CharFilter(
        field_name="creator__name", label=_("Creator name")
    )
    is_periodic_display = drf_filters.BooleanFilter(
        field_name="is_periodic", label=_("Periodic execution")
    )

    class Meta:
        model = Job
        fields = [
            "id", "name", "args", "type", "crontab", "interval",
            "creator__name", "is_periodic_display",
        ]
