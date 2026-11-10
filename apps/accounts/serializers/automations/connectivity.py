from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import AutomationTypes
from accounts.models import ConnectivityRecord, VerifyAccountAutomation
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
    class Meta(AutomationExecutionSerializer.Meta):
        fields = AutomationExecutionSerializer.Meta.fields + ['summary', 'result']
        read_only_fields = AutomationExecutionSerializer.Meta.read_only_fields + [
            'id', 'summary', 'result',
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


class ConnectivityRecordSerializer(serializers.ModelSerializer):
    execution = serializers.UUIDField(source='execution_id', read_only=True, label=_('Execution'))
    type = LabeledChoiceField(choices=ConnectivityRecord.Type.choices, read_only=True, label=_('Type'))
    status = LabeledChoiceField(choices=ConnectivityRecord.Status.choices, read_only=True, label=_('Result'))

    class Meta:
        model = ConnectivityRecord
        fields = [
            'id', 'execution', 'type', 'asset', 'asset_id', 'asset_address',
            'account', 'account_id', 'username', 'privileged', 'status',
            'date_start', 'date_finished', 'error',
        ]
        read_only_fields = fields
