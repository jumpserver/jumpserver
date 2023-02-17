# -*- coding: utf-8 -*-
#
from importlib import import_module

from django.conf import settings
from django.db.models import F, Value, CharField, Q
from rest_framework import generics
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated

from common.api import JMSGenericViewSet
from common.drf.filters import DatetimeRangeFilter
from common.plugins.es import QuerySet as ESQuerySet
from orgs.mixins.api import OrgGenericViewSet, OrgBulkModelViewSet
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


class JobAuditViewSet(OrgBulkModelViewSet):
    model = JobLog
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    search_fields = ['creator__name', 'material']
    serializer_class = JobLogSerializer
    ordering = ['-date_start']
    http_method_names = ('get', 'head', 'options')


class FTPLogViewSet(CreateModelMixin, ListModelMixin, OrgGenericViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'asset', 'account', 'filename']
    search_fields = filterset_fields
    ordering = ['-date_start']


class UserLoginCommonMixin:
    queryset = UserLoginLog.objects.all()
    serializer_class = UserLoginLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['id', 'username', 'ip', 'city', 'type', 'status', 'mfa']
    search_fields = ['id', 'username', 'ip', 'city']


class UserLoginLogViewSet(
    UserLoginCommonMixin, RetrieveModelMixin, ListModelMixin, JMSGenericViewSet
):
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


class MyLoginLogAPIView(UserLoginCommonMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(username=self.request.user.username)
        return qs


class ResourceActivityAPIView(generics.ListAPIView):
    serializer_class = ActivityUnionLogSerializer
    rbac_perms = {
        'GET': 'audits.view_activitylog',
    }

    @staticmethod
    def get_operate_log_qs(fields, limit=30, resource_id=None):
        q = Q(resource_id=resource_id)
        user = User.objects.filter(id=resource_id).first()
        if user:
            q |= Q(user=str(user))
        queryset = OperateLog.objects.filter(q).annotate(
            r_type=Value(ActivityChoices.operate_log, CharField()),
            r_detail_id=F('id'), r_detail=Value(None, CharField()),
            r_user=F('user'), r_action=F('action'),
        ).values(*fields)[:limit]
        return queryset

    @staticmethod
    def get_activity_log_qs(fields, limit=30, **filters):
        queryset = ActivityLog.objects.filter(**filters).annotate(
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
        with tmp_to_root_org():
            qs1 = self.get_operate_log_qs(fields, resource_id=resource_id)
            qs2 = self.get_activity_log_qs(fields, resource_id=resource_id)
            queryset = qs2.union(qs1)
        return queryset.order_by('-datetime')[:limit]


class OperateLogViewSet(RetrieveModelMixin, ListModelMixin, OrgGenericViewSet):
    model = OperateLog
    serializer_class = OperateLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'action', 'resource_type', 'resource', 'remote_addr']
    search_fields = ['resource']
    ordering = ['-datetime']

    def get_serializer_class(self):
        if self.request.query_params.get('type') == 'action_detail':
            return OperateLogActionDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        with tmp_to_root_org():
            qs = OperateLog.objects.filter(
                Q(org_id=current_org.id) | Q(org_id=Organization.SYSTEM_ID)
            )
        es_config = settings.OPERATE_LOG_ELASTICSEARCH_CONFIG
        if es_config:
            engine_mod = import_module(TYPE_ENGINE_MAPPING['es'])
            store = engine_mod.OperateLogStore(es_config)
            if store.ping(timeout=2):
                qs = ESQuerySet(store)
                qs.model = OperateLog
        return qs


class PasswordChangeLogViewSet(ListModelMixin, JMSGenericViewSet):
    queryset = PasswordChangeLog.objects.all()
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
