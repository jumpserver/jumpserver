from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as drf_filters
from rest_framework import mixins

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.filters import AutomationExecutionFilterSet
from accounts.models import VerifyAccountAutomation
from assets.const import AutomationTypes as AssetAutomationTypes
from assets.models import AutomationExecution as AssetAutomationExecution, BaseAutomation, PingAutomation
from assets.tasks import execute_asset_automation_task
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from .base import (
    AutomationExecutionViewSet, AutomationAssetsListApi, AutomationRemoveAssetApi,
    AutomationAddAssetApi, AutomationNodeAddRemoveApi,
)

__all__ = [
    'VerifyAccountAutomationViewSet', 'VerifyAccountExecutionViewSet',
    'VerifyAccountAssetsListApi', 'VerifyAccountRemoveAssetApi',
    'VerifyAccountAddAssetApi', 'VerifyAccountNodeAddRemoveApi',
    'PingAutomationViewSet', 'PingExecutionViewSet',
    'PingAssetsListApi', 'PingRemoveAssetApi',
    'PingAddAssetApi', 'PingNodeAddRemoveApi',
    'ConnectivityAutomationViewSet', 'ConnectivityExecutionViewSet',
]


class ConnectivityAutomationViewSet(mixins.ListModelMixin, OrgGenericViewSet):
    model = BaseAutomation
    serializer_class = serializers.ConnectivityAutomationListSerializer
    filterset_fields = ('name', 'type', 'is_active', 'is_periodic')
    search_fields = ('name',)
    rbac_perms = {
        'list': 'accounts.view_verifyaccountautomation | assets.view_pingautomation',
    }

    def get_queryset(self):
        permissions = {
            AutomationTypes.verify_account: 'accounts.view_verifyaccountautomation',
            AssetAutomationTypes.ping: 'assets.view_pingautomation',
        }
        allowed_types = [
            task_type for task_type, permission in permissions.items()
            if self.request.user.has_perm(permission)
        ]
        return super().get_queryset().filter(type__in=allowed_types)


class ConnectivityExecutionFilterSet(AutomationExecutionFilterSet):
    type = drf_filters.ChoiceFilter(
        choices=[
            (AutomationTypes.verify_account, _('Account')),
            (AssetAutomationTypes.ping, _('Asset')),
        ],
        label=_('Type'),
    )

    class Meta(AutomationExecutionFilterSet.Meta):
        model = AssetAutomationExecution
        fields = AutomationExecutionFilterSet.Meta.fields + ['type']


class ConnectivityExecutionViewSet(mixins.ListModelMixin, OrgGenericViewSet):
    model = AssetAutomationExecution
    serializer_class = serializers.ConnectivityExecutionListSerializer
    filterset_class = ConnectivityExecutionFilterSet
    search_fields = ('id', 'trigger', 'automation__name')
    ordering = ('-date_start', '-id')
    extra_ordering_fields = ['id']
    rbac_perms = {
        'list': 'accounts.view_verifyaccountexecution | assets.view_pingexecution',
    }

    def get_queryset(self):
        permissions = {
            AutomationTypes.verify_account: 'accounts.view_verifyaccountexecution',
            AssetAutomationTypes.ping: 'assets.view_pingexecution',
        }
        allowed_types = [
            execution_type for execution_type, permission in permissions.items()
            if self.request.user.has_perm(permission)
        ]
        return super().get_queryset().filter(type__in=allowed_types).select_related('automation')


class VerifyAccountAutomationViewSet(OrgBulkModelViewSet):
    model = VerifyAccountAutomation
    filterset_fields = ('name', 'is_active', 'is_periodic')
    search_fields = ('name',)
    serializer_classes = {
        'default': serializers.VerifyAccountAutomationSerializer,
        'list': serializers.VerifyAccountAutomationListSerializer,
    }


class VerifyAccountExecutionViewSet(AutomationExecutionViewSet):
    tp = AutomationTypes.verify_account
    serializer_class = serializers.VerifyAccountExecutionSerializer
    rbac_perms = {
        'list': 'accounts.view_verifyaccountexecution',
        'retrieve': 'accounts.view_verifyaccountexecution',
        'create': 'accounts.add_verifyaccountexecution',
        'report': 'accounts.view_verifyaccountexecution',
    }

    def get_queryset(self):
        return super().get_queryset().filter(type=self.tp)


class PingAutomationViewSet(OrgBulkModelViewSet):
    model = PingAutomation
    filterset_fields = ('name', 'is_active', 'is_periodic')
    search_fields = ('name',)
    serializer_classes = {
        'default': serializers.PingAutomationSerializer,
        'list': serializers.PingAutomationListSerializer,
    }


class PingExecutionFilterSet(AutomationExecutionFilterSet):
    class Meta(AutomationExecutionFilterSet.Meta):
        model = AssetAutomationExecution


class PingExecutionViewSet(AutomationExecutionViewSet):
    tp = AssetAutomationTypes.ping
    execute_task = execute_asset_automation_task
    serializer_class = serializers.PingExecutionSerializer
    filterset_class = PingExecutionFilterSet
    rbac_perms = {
        'list': 'assets.view_pingexecution',
        'retrieve': 'assets.view_pingexecution',
        'create': 'assets.add_pingexecution',
        'report': 'assets.view_pingexecution',
    }

    def get_queryset(self):
        return AssetAutomationExecution.objects.filter(type=self.tp)


class VerifyAccountAssetsListApi(AutomationAssetsListApi):
    model = VerifyAccountAutomation
    perm_model = VerifyAccountAutomation


class VerifyAccountRemoveAssetApi(AutomationRemoveAssetApi):
    model = VerifyAccountAutomation


class VerifyAccountAddAssetApi(AutomationAddAssetApi):
    model = VerifyAccountAutomation


class VerifyAccountNodeAddRemoveApi(AutomationNodeAddRemoveApi):
    model = VerifyAccountAutomation


class PingAssetsListApi(AutomationAssetsListApi):
    model = PingAutomation
    perm_model = PingAutomation


class PingRemoveAssetApi(AutomationRemoveAssetApi):
    model = PingAutomation


class PingAddAssetApi(AutomationAddAssetApi):
    model = PingAutomation


class PingNodeAddRemoveApi(AutomationNodeAddRemoveApi):
    model = PingAutomation
