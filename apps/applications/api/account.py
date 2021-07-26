# coding: utf-8
#

from rest_framework import generics
from django_filters import rest_framework as filters
from django.conf import settings
from django.db.models import F

from common.drf.filters import BaseFilterSet
from perms.models import ApplicationPermission
from ..hands import IsOrgAdminOrAppUser, IsOrgAdmin, NeedMFAVerify
from .. import serializers


class AccountFilterSet(BaseFilterSet):
    username = filters.CharFilter(field_name='username')
    app = filters.CharFilter(field_name='applications', lookup_expr='exact')
    app_name = filters.CharFilter(field_name='app_name', lookup_expr='exact')
    app_type = filters.CharFilter(field_name='app_type', lookup_expr='exact')
    app_category = filters.CharFilter(field_name='app_category', lookup_expr='exact')

    class Meta:
        model = ApplicationPermission
        fields = []


class ApplicationAccountListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin, )
    search_fields = ['username', 'app_name']
    filterset_class = AccountFilterSet
    filterset_fields = ['username', 'app_name', 'app_type', 'app_category']
    serializer_class = serializers.ApplicationAccountSerializer

    def get_queryset(self):
        queryset = ApplicationPermission.objects.all()\
            .annotate(username=F('system_users__username')) \
            .annotate(password=F('system_users__password'))\
            .annotate(app_name=F("applications__name")) \
            .annotate(app_category=F("applications__category")) \
            .annotate(app_type=F("applications__type"))
        return queryset


class ApplicationAccountAuthInfoListApi(ApplicationAccountListApi):
    serializer_class = serializers.ApplicationAccountWithAuthInfoSerializer
    http_method_names = ['get']
    permission_classes = [IsOrgAdminOrAppUser]

    def get_permissions(self):
        if settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]
        return super().get_permissions()
