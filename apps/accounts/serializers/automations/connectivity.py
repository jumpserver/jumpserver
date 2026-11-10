from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import AutomationTypes
from accounts.models import VerifyAccountAutomation
from assets.const import AutomationTypes as AssetAutomationTypes
from assets.models import BaseAutomation, PingAutomation
from assets.serializers.automations import AutomationExecutionSerializer
from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from .base import AutomationListSerializerMixin, BaseAutomationSerializer

__all__ = [
    'VerifyAccountAutomationSerializer', 'VerifyAccountAutomationListSerializer',
    'PingAutomationSerializer', 'PingAutomationListSerializer',
    'VerifyAccountExecutionSerializer', 'PingExecutionSerializer',
    'ConnectivityAutomationListSerializer', 'ConnectivityExecutionListSerializer',
    'ConnectivityRecordSerializer',
]


class ConnectivityAutomationListSerializer(AutomationListSerializerMixin, BaseAutomationSerializer):
    type = LabeledChoiceField(
        choices=[
            (AutomationTypes.verify_account, _('Account')),
            (AssetAutomationTypes.ping, _('Asset')),
        ],
        read_only=True, label=_('Type'),
    )

    class Meta(BaseAutomationSerializer.Meta):
        model = BaseAutomation
        relation_count_fields = {'assets_amount': 'assets', 'nodes_amount': 'nodes'}
        fields = [
            field for field in BaseAutomationSerializer.Meta.fields
            if field not in ('accounts', 'assets', 'nodes')
        ] + ['assets_amount', 'nodes_amount']
        read_only_fields = fields


class VerifyAccountAutomationSerializer(BaseAutomationSerializer):
    accounts = serializers.ListField(
        child=serializers.CharField(max_length=128), required=False,
        label=_('Accounts'),
        help_text=_('Account usernames. Leave empty to test all active accounts on the selected assets.'),
    )

    class Meta(BaseAutomationSerializer.Meta):
        model = VerifyAccountAutomation

    @property
    def model_type(self):
        return AutomationTypes.verify_account


class VerifyAccountAutomationListSerializer(
    AutomationListSerializerMixin, VerifyAccountAutomationSerializer
):
    class Meta(VerifyAccountAutomationSerializer.Meta):
        relation_count_fields = {'assets_amount': 'assets', 'nodes_amount': 'nodes'}
        fields = [
            field for field in VerifyAccountAutomationSerializer.Meta.fields
            if field not in ('assets', 'nodes')
        ] + ['assets_amount', 'nodes_amount']


class PingAutomationSerializer(BaseAutomationSerializer):
    class Meta(BaseAutomationSerializer.Meta):
        model = PingAutomation
        fields = [
            field for field in BaseAutomationSerializer.Meta.fields
            if field != 'accounts'
        ]

    @property
    def model_type(self):
        return AssetAutomationTypes.ping


class PingAutomationListSerializer(AutomationListSerializerMixin, PingAutomationSerializer):
    class Meta(PingAutomationSerializer.Meta):
        relation_count_fields = {'assets_amount': 'assets', 'nodes_amount': 'nodes'}
        fields = [
            field for field in PingAutomationSerializer.Meta.fields
            if field not in ('assets', 'nodes')
        ] + ['assets_amount', 'nodes_amount']


class ConnectivityExecutionSerializer(AutomationExecutionSerializer):
    account_results = serializers.SerializerMethodField(label=_('Accounts'))

    @staticmethod
    def get_account_results(obj):
        from assets.automations.base.account_results import get_execution_account_results
        return get_execution_account_results(obj)

    class Meta(AutomationExecutionSerializer.Meta):
        fields = AutomationExecutionSerializer.Meta.fields + ['summary', 'result', 'account_results']
        read_only_fields = AutomationExecutionSerializer.Meta.read_only_fields + [
            'id', 'summary', 'result', 'account_results',
        ]


class ConnectivityExecutionListSerializer(AutomationExecutionSerializer):
    type = LabeledChoiceField(
        choices=[
            (AutomationTypes.verify_account, _('Account')),
            (AssetAutomationTypes.ping, _('Asset')),
        ],
        read_only=True, label=_('Type'),
    )

    class Meta(AutomationExecutionSerializer.Meta):
        fields = AutomationExecutionSerializer.Meta.fields + ['type']
        read_only_fields = fields


class VerifyAccountExecutionSerializer(ConnectivityExecutionSerializer):
    automation = ObjectRelatedField(
        queryset=VerifyAccountAutomation.objects, required=True,
    )


class PingExecutionSerializer(ConnectivityExecutionSerializer):
    automation = ObjectRelatedField(queryset=PingAutomation.objects, required=True)


class ConnectivityRecordSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    execution = serializers.UUIDField(read_only=True, label=_('Execution'))
    type = LabeledChoiceField(choices=[('ping', _('Asset')), ('verify_account', _('Account'))], read_only=True, label=_('Type'))
    asset = serializers.CharField(read_only=True, label=_('Asset'))
    asset_address = serializers.CharField(read_only=True, label=_('Address'))
    account = serializers.CharField(read_only=True, label=_('Account'))
    username = serializers.CharField(read_only=True, label=_('Username'))
    privileged = serializers.BooleanField(read_only=True, allow_null=True, label=_('Privileged'))
    status = LabeledChoiceField(choices=[('success', _('Success')), ('failed', _('Failed'))], read_only=True, label=_('Result'))
    date_start = serializers.DateTimeField(read_only=True, allow_null=True, label=_('Date start'))
    date_finished = serializers.DateTimeField(read_only=True, allow_null=True, label=_('Date finished'))
    error = serializers.CharField(read_only=True, label=_('Error'))
