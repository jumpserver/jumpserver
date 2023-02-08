# -*- coding: utf-8 -*-
#
from importlib import import_module

from django.conf import settings
from django.db.models import F, Value, CharField
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin

from ops.models.job import JobAuditLog
from common.api import JMSGenericViewSet
from common.drf.filters import DatetimeRangeFilter
from common.plugins.es import QuerySet as ESQuerySet
from orgs.utils import current_org, tmp_to_root_org
from orgs.mixins.api import OrgGenericViewSet, OrgBulkModelViewSet
from .backends import TYPE_ENGINE_MAPPING
from .const import ActivityChoices
from .models import FTPLog, UserLoginLog, OperateLog, PasswordChangeLog, ActivityLog
from .serializers import FTPLogSerializer, UserLoginLogSerializer, JobAuditLogSerializer
from .serializers import (
    OperateLogSerializer, OperateLogActionDetailSerializer,
    PasswordChangeLogSerializer, ActivityOperatorLogSerializer,
)


class JobAuditViewSet(OrgBulkModelViewSet):
    model = JobAuditLog
    serializer_class = JobAuditLogSerializer
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


class UserLoginLogViewSet(UserLoginCommonMixin, ListModelMixin, JMSGenericViewSet):

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
    serializer_class = ActivityOperatorLogSerializer
    rbac_perms = {
        'GET': 'audits.view_activitylog',
    }

    @staticmethod
    def get_operate_log_qs(fields, limit=30, **filters):
        queryset = OperateLog.objects.filter(**filters).annotate(
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
        return queryset[:limit]


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
        qs = OperateLog.objects.all()
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
        users = current_org.get_members()
        queryset = super().get_queryset().filter(
            user__in=[user.__str__() for user in users]
        )
        return queryset

# Todo: 看看怎么搞
# class CommandExecutionViewSet(ListModelMixin, OrgGenericViewSet):
#     model = CommandExecution
#     serializer_class = CommandExecutionSerializer
#     extra_filter_backends = [DatetimeRangeFilter]
#     date_range_filter_fields = [
#         ('date_start', ('date_from', 'date_to'))
#     ]
#     filterset_fields = [
#         'user__name', 'user__username', 'command',
#         'account', 'is_finished'
#     ]
#     search_fields = [
#         'command', 'user__name', 'user__username',
#         'account__username',
#     ]
#     ordering = ['-date_created']
#
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         if getattr(self, 'swagger_fake_view', False):
#             return queryset.model.objects.none()
#         if current_org.is_root():
#             return queryset
#         # queryset = queryset.filter(run_as__org_id=current_org.org_id())
#         return queryset
#
#
# class CommandExecutionHostRelationViewSet(OrgRelationMixin, OrgBulkModelViewSet):
#     serializer_class = CommandExecutionHostsRelationSerializer
#     m2m_field = CommandExecution.hosts.field
#     filterset_fields = [
#         'id', 'asset', 'commandexecution'
#     ]
#     search_fields = ('asset__name', )
#     http_method_names = ['options', 'get']
#     rbac_perms = {
#         'GET': 'ops.view_commandexecution',
#         'list': 'ops.view_commandexecution',
#     }
#
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         queryset = queryset.annotate(
#             asset_display=Concat(
#                 F('asset__name'), Value('('),
#                 F('asset__address'), Value(')')
#             )
#         )
#         return queryset
