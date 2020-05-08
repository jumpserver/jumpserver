# -*- coding: utf-8 -*-
#
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin

from common.mixins.api import CommonApiMixin
from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor, IsOrgAdmin
from common.drf.filters import DatetimeRangeFilter
from orgs.mixins.api import OrgGenericViewSet
from orgs.utils import current_org
from .models import FTPLog, UserLoginLog
from .serializers import FTPLogSerializer, UserLoginLogSerializer


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


class UserLoginLogViewSet(CommonApiMixin,
                          ListModelMixin,
                          GenericViewSet):
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
