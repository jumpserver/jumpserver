# -*- coding: utf-8 -*-
#
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin

from common.mixins.api import CommonApiMixin
from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor, IsOrgAdmin
from common.drf.filters import DatetimeRangeFilter, current_user_filter
from common.api import CommonGenericViewSet
from orgs.mixins.api import OrgGenericViewSet
from orgs.utils import current_org
from ops.models import CommandExecution
from .models import FTPLog, UserLoginLog, OperateLog, PasswordChangeLog
from .serializers import FTPLogSerializer, UserLoginLogSerializer, CommandExecutionSerializer
from .serializers import OperateLogSerializer, PasswordChangeLogSerializer
from .filters import CurrentOrgMembersFilter


class FTPLogViewSet(ListModelMixin, OrgGenericViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor,)
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'asset', 'system_user']
    search_fields = ['filename']


class UserLoginLogViewSet(ListModelMixin,
                          CommonGenericViewSet):
    queryset = UserLoginLog.objects.all()
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    serializer_class = UserLoginLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['username']
    search_fields = ['ip', 'city', 'username']

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
    filterset_fields = ['user', 'action', 'resource_type']
    search_fields = ['filename']
    ordering_fields = ['-datetime']


class PasswordChangeLogViewSet(ListModelMixin, CommonGenericViewSet):
    queryset = PasswordChangeLog.objects.all()
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    serializer_class = PasswordChangeLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user']
    ordering_fields = ['-datetime']

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
    extra_filter_backends = [DatetimeRangeFilter, current_user_filter(), CurrentOrgMembersFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    search_fields = ['command']
    ordering_fields = ['-date_created']
