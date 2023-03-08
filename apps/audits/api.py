# -*- coding: utf-8 -*-
#
from importlib import import_module

from django.conf import settings
from django.db.models import F, Value, CharField, Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from common.drf.filters import DatetimeRangeFilter
from common.plugins.es import QuerySet as ESQuerySet
from common.utils import is_uuid
from orgs.mixins.api import OrgReadonlyModelViewSet, OrgModelViewSet
from orgs.utils import current_org, tmp_to_root_org
from orgs.models import Organization
from users.models import User
from .backends import TYPE_ENGINE_MAPPING
from .const import ActivityChoices
from .models import FTPLog, UserLoginLog, OperateLog, PasswordChangeLog, ActivityLog, JobLog
from .serializers import FTPLogSerializer, UserLoginLogSerializer, JobLogSerializer
from .serializers import (
    OperateLogSerializer, OperateLogActionDetailSerializer,
    PasswordChangeLogSerializer, ActivityUnionLogSerializer,
)


class JobAuditViewSet(OrgReadonlyModelViewSet):
    model = JobLog
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    search_fields = ['creator__name', 'material']
    filterset_fields = ['creator__name', 'material']
    serializer_class = JobLogSerializer
    ordering = ['-date_start']


class FTPLogViewSet(OrgModelViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'asset', 'account', 'filename']
    search_fields = filterset_fields
    ordering = ['-date_start']
    http_method_names = ['post', 'get', 'head', 'options']


class UserLoginCommonMixin:
    model = UserLoginLog
    serializer_class = UserLoginLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['id', 'username', 'ip', 'city', 'type', 'status', 'mfa']
    search_fields = ['id', 'username', 'ip', 'city']


class UserLoginLogViewSet(UserLoginCommonMixin, OrgReadonlyModelViewSet):
    @staticmethod
    def get_org_members():
        users = current_org.get_members().values_list('username', flat=True)
        return users

    def get_queryset(self):
        queryset = super().get_queryset()
        if current_org.is_root():
            return queryset
        users = self.get_org_members()
        queryset = queryset.filter(username__in=users)
        return queryset


class MyLoginLogViewSet(UserLoginCommonMixin, OrgReadonlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(username=self.request.user.username)
        return qs


class ResourceActivityAPIView(generics.ListAPIView):
    serializer_class = ActivityUnionLogSerializer
    ordering_fields = ['datetime']
    rbac_perms = {
        'GET': 'audits.view_activitylog',
    }

    @staticmethod
    def get_operate_log_qs(fields, limit, org_q, resource_id=None):
        q, user = Q(resource_id=resource_id), None
        if is_uuid(resource_id):
            user = User.objects.filter(id=resource_id).first()
        if user is not None:
            q |= Q(user=str(user))
        queryset = OperateLog.objects.filter(q, org_q).annotate(
            r_type=Value(ActivityChoices.operate_log, CharField()),
            r_detail_id=F('id'), r_detail=Value(None, CharField()),
            r_user=F('user'), r_action=F('action'),
        ).values(*fields)[:limit]
        return queryset

    @staticmethod
    def get_activity_log_qs(fields, limit, org_q, **filters):
        queryset = ActivityLog.objects.filter(org_q, **filters).annotate(
            r_type=F('type'), r_detail_id=F('detail_id'),
            r_detail=F('detail'), r_user=Value(None, CharField()),
            r_action=Value(None, CharField()),
        ).values(*fields)[:limit]
        return queryset

    def get_queryset(self):
        limit = 30
        resource_id = self.request.query_params.get('resource_id')
        fields = (
            'id', 'datetime', 'r_detail', 'r_detail_id',
            'r_user', 'r_action', 'r_type'
        )
        org_q = Q(org_id=Organization.SYSTEM_ID) | Q(org_id=current_org.id)
        with tmp_to_root_org():
            qs1 = self.get_operate_log_qs(fields, limit, org_q, resource_id=resource_id)
            qs2 = self.get_activity_log_qs(fields, limit, org_q, resource_id=resource_id)
            queryset = qs2.union(qs1)
        return queryset.order_by('-datetime')[:limit]


class OperateLogViewSet(OrgReadonlyModelViewSet):
    model = OperateLog
    serializer_class = OperateLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = [
        'user', 'action', 'resource_type', 'resource',
        'remote_addr'
    ]
    search_fields = ['resource', 'user']
    ordering = ['-datetime']

    def get_serializer_class(self):
        if self.request.query_params.get('type') == 'action_detail':
            return OperateLogActionDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        org_q = Q(org_id=current_org.id)
        with tmp_to_root_org():
            qs = OperateLog.objects.filter(org_q)
        es_config = settings.OPERATE_LOG_ELASTICSEARCH_CONFIG
        if es_config:
            engine_mod = import_module(TYPE_ENGINE_MAPPING['es'])
            store = engine_mod.OperateLogStore(es_config)
            if store.ping(timeout=2):
                qs = ESQuerySet(store)
                qs.model = OperateLog
        return qs


class PasswordChangeLogViewSet(OrgReadonlyModelViewSet):
    model = PasswordChangeLog
    serializer_class = PasswordChangeLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'change_by', 'remote_addr']
    search_fields = filterset_fields
    ordering = ['-datetime']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not current_org.is_root():
            users = current_org.get_members()
            queryset = queryset.filter(
                user__in=[str(user) for user in users]
            )
        return queryset
