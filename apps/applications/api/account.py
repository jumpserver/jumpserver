# coding: utf-8
#

from django_filters import rest_framework as filters
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat
from django.http import Http404

from common.drf.filters import BaseFilterSet
from common.drf.api import JMSModelViewSet
from common.utils import unique
from perms.models import ApplicationPermission
from ..hands import IsOrgAdminOrAppUser, IsOrgAdmin, NeedMFAVerify
from .. import serializers


class AccountFilterSet(BaseFilterSet):
    username = filters.CharFilter(field_name='username')
    app = filters.CharFilter(field_name='applications', lookup_expr='exact')
    app_name = filters.CharFilter(field_name='app_name', lookup_expr='exact')

    class Meta:
        model = ApplicationPermission
        fields = ['type', 'category']


class ApplicationAccountViewSet(JMSModelViewSet):
    permission_classes = (IsOrgAdmin, )
    search_fields = ['username', 'app_name']
    filterset_class = AccountFilterSet
    filterset_fields = ['username', 'app_name', 'type', 'category']
    serializer_class = serializers.ApplicationAccountSerializer

    http_method_names = ['get', 'put', 'patch', 'options']

    def get_queryset(self):
        queryset = ApplicationPermission.objects.all() \
            .annotate(uid=Concat(
                'applications', Value('_'), 'system_users', output_field=CharField()
             )) \
            .annotate(systemuser=F('system_users')) \
            .annotate(systemuser_display=F('system_users__name')) \
            .annotate(username=F('system_users__username')) \
            .annotate(password=F('system_users__password')) \
            .annotate(app=F('applications')) \
            .annotate(app_name=F("applications__name")) \
            .values('username', 'password', 'systemuser', 'systemuser_display',
                    'app', 'app_name', 'category', 'type', 'uid')
        return queryset

    def get_object(self):
        obj = self.get_queryset().filter(
            uid=self.kwargs['pk']
        ).first()
        if not obj:
            raise Http404()
        return obj

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset_list = unique(queryset, key=lambda x: (x['app'], x['systemuser']))
        return queryset_list


class ApplicationAccountSecretViewSet(ApplicationAccountViewSet):
    serializer_class = serializers.ApplicationAccountSecretSerializer
    permission_classes = [IsOrgAdminOrAppUser, NeedMFAVerify]
    http_method_names = ['get', 'options']

