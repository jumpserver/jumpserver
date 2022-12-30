from accounts.models import PushAccountAutomation
from .change_secret import (
    ChangeSecretAutomationSerializer, ChangeSecretUpdateAssetSerializer,
    ChangeSecretUpdateNodeSerializer
)


class PushAccountAutomationSerializer(ChangeSecretAutomationSerializer):
    class Meta(ChangeSecretAutomationSerializer.Meta):
        model = PushAccountAutomation

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        excludes = ['recipients', 'is_periodic', 'interval', 'crontab']
        fields = [f for f in fields if f not in excludes]
        fields[fields.index('accounts')] = 'username'
        return fields


class PushAccountUpdateAssetSerializer(ChangeSecretUpdateAssetSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateAssetSerializer.Meta.fields


class PushAccountUpdateNodeSerializer(ChangeSecretUpdateNodeSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateNodeSerializer.Meta.fields
