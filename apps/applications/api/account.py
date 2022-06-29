# coding: utf-8
#

from django_filters import rest_framework as filters
from django.db.models import Q

from common.drf.filters import BaseFilterSet
from common.drf.api import JMSBulkModelViewSet
from common.mixins import RecordViewLogMixin
from common.permissions import UserConfirmation
from authentication.const import ConfirmType
from rbac.permissions import RBACPermission
from assets.models import SystemUser
from ..models import Account
from .. import serializers


class AccountFilterSet(BaseFilterSet):
    username = filters.CharFilter(method='do_nothing')
    type = filters.CharFilter(field_name='type', lookup_expr='exact')
    category = filters.CharFilter(field_name='category', lookup_expr='exact')
    app_display = filters.CharFilter(field_name='app_display', lookup_expr='exact')

    class Meta:
        model = Account
        fields = ['app', 'systemuser']

    @property
    def qs(self):
        qs = super().qs
        qs = self.filter_username(qs)
        return qs

    def filter_username(self, qs):
        username = self.get_query_param('username')
        if not username:
            return qs
        q = Q(username=username) | Q(systemuser__username=username)
        qs = qs.filter(q).distinct()
        return qs


class ApplicationAccountViewSet(JMSBulkModelViewSet):
    model = Account
    search_fields = ['username', 'app_display']
    filterset_class = AccountFilterSet
    filterset_fields = ['username', 'app_display', 'type', 'category', 'app']
    serializer_class = serializers.AppAccountSerializer

    def get_queryset(self):
        queryset = Account.get_queryset()
        return queryset


class SystemUserAppRelationViewSet(ApplicationAccountViewSet):
    perm_model = SystemUser


class ApplicationAccountSecretViewSet(RecordViewLogMixin, ApplicationAccountViewSet):
    serializer_class = serializers.AppAccountSecretSerializer
    permission_classes = [RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    http_method_names = ['get', 'options']
    rbac_perms = {
        'retrieve': 'applications.view_applicationaccountsecret',
        'list': 'applications.view_applicationaccountsecret',
    }
