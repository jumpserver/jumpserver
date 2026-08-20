from accounts.const import AutomationTypes
from accounts.models import PushAccountAutomation, PushSecretRecord
from .base import AutomationListSerializerMixin
from .change_secret import (
    ChangeSecretAutomationSerializer, ChangeSecretUpdateAssetSerializer,
    ChangeSecretUpdateNodeSerializer, ChangeSecretRecordSerializer
)


class PushAccountAutomationSerializer(ChangeSecretAutomationSerializer):
    class Meta(ChangeSecretAutomationSerializer.Meta):
        model = PushAccountAutomation
        fields = [
            n for n in ChangeSecretAutomationSerializer.Meta.fields
            if n not in ['recipients']
        ]

    @property
    def model_type(self):
        return AutomationTypes.push_account


class PushAccountAutomationListSerializer(AutomationListSerializerMixin, PushAccountAutomationSerializer):
    class Meta(PushAccountAutomationSerializer.Meta):
        relation_count_fields = {'assets_amount': 'assets', 'nodes_amount': 'nodes'}
        fields = [
            f for f in PushAccountAutomationSerializer.Meta.fields
            if f not in ('assets', 'nodes', 'recipients')
        ] + ['assets_amount', 'nodes_amount']


class PushSecretRecordSerializer(ChangeSecretRecordSerializer):
    class Meta(ChangeSecretRecordSerializer.Meta):
        model = PushSecretRecord
        fields = [
            field for field in ChangeSecretRecordSerializer.Meta.fields
            if field not in (
                'verification_status', 'verification_error', 'date_verified',
            )
        ]
        read_only_fields = fields


class PushAccountUpdateAssetSerializer(ChangeSecretUpdateAssetSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateAssetSerializer.Meta.fields


class PushAccountUpdateNodeSerializer(ChangeSecretUpdateNodeSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateNodeSerializer.Meta.fields
