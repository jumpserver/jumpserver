# -*- coding: utf-8 -*-
#
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from django.db.models import F, Value
from django.db.models.functions import Concat

from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor, IsOrgAdmin
from common.drf.filters import DatetimeRangeFilter
from common.api import CommonGenericViewSet
from orgs.mixins.api import OrgGenericViewSet, OrgBulkModelViewSet, OrgRelationMixin
from orgs.utils import current_org
from ops.models import CommandExecution
from .models import FTPLog, UserLoginLog, OperateLog, PasswordChangeLog
from .serializers import FTPLogSerializer, UserLoginLogSerializer, CommandExecutionSerializer
from .serializers import OperateLogSerializer, PasswordChangeLogSerializer, CommandExecutionHostsRelationSerializer


class FTPLogViewSet(CreateModelMixin,
                    ListModelMixin,
                    OrgGenericViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor,)
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filter_fields = ['user', 'asset', 'system_user', 'filename']
    search_fields = filter_fields
    ordering = ['-date_start']


class UserLoginLogViewSet(ListModelMixin, CommonGenericViewSet):
    queryset = UserLoginLog.objects.all()
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    serializer_class = UserLoginLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filter_fields = ['username', 'ip', 'city', 'type', 'status', 'mfa']
    search_fields =['username', 'ip', 'city']

    @staticmethod
    def get_org_members():
        users = current_org.get_org_members().values_list('username', flat=True)
        return users

    def get_queryset(self):
        queryset = super().get_queryset()
        if not current_org.is_default():
            users = self.get_org_members()
            queryset = queryset.filter(username__in=users)
        return queryset


class OperateLogViewSet(ListModelMixin, OrgGenericViewSet):
    model = OperateLog
    serializer_class = OperateLogSerializer
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filter_fields = ['user', 'action', 'resource_type', 'resource', 'remote_addr']
    search_fields = ['resource']
    ordering = ['-datetime']


class PasswordChangeLogViewSet(ListModelMixin, CommonGenericViewSet):
    queryset = PasswordChangeLog.objects.all()
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    serializer_class = PasswordChangeLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filter_fields = ['user', 'change_by', 'remote_addr']
    ordering = ['-datetime']

    def get_queryset(self):
        users = current_org.get_org_members()
        queryset = super().get_queryset().filter(
            user__in=[user.__str__() for user in users]
        )
        return queryset


class CommandExecutionViewSet(ListModelMixin, OrgGenericViewSet):
    model = CommandExecution
    serializer_class = CommandExecutionSerializer
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filter_fields = ['user__name', 'command', 'run_as__name', 'is_finished']
    search_fields = ['command', 'user__name', 'run_as__name']
    ordering = ['-date_created']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(run_as__org_id=current_org.org_id())
        return queryset


class CommandExecutionHostRelationViewSet(OrgRelationMixin, OrgBulkModelViewSet):
    serializer_class = CommandExecutionHostsRelationSerializer
    m2m_field = CommandExecution.hosts.field
    permission_classes = (IsOrgAdmin,)
    filter_fields = [
        'id', 'asset', 'commandexecution'
    ]
    search_fields = ('asset__hostname', )
    http_method_names = ['options', 'get']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            asset_display=Concat(
                F('asset__hostname'), Value('('),
                F('asset__ip'), Value(')')
            )
        )
        return queryset
