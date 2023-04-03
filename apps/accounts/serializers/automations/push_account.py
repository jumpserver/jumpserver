from rest_framework import serializers

from accounts.const import AutomationTypes
from accounts.models import PushAccountAutomation
from assets.const import AllTypes
from common.serializers import MethodSerializer
from .change_secret import (
    ChangeSecretAutomationSerializer, ChangeSecretUpdateAssetSerializer,
    ChangeSecretUpdateNodeSerializer
)


class PushAccountAutomationSerializer(ChangeSecretAutomationSerializer):
    params = MethodSerializer(required=False)

    class Meta(ChangeSecretAutomationSerializer.Meta):
        model = PushAccountAutomation
        fields = ['params'] + [
            n for n in ChangeSecretAutomationSerializer.Meta.fields
            if n not in ['recipients']
        ]

    def get_params_serializer(self):
        default_serializer = serializers.JSONField(
            required=False, style={'base_template': 'textarea.html'}
        )
        request = self.context.get('request')
        if request:
            platform_types = request.query_params.get('platform_types')
        else:
            platform_types = None

        if platform_types:
            platform_types = platform_types.split(',')
            push_account_automation_methods = list(
                filter(
                    lambda x: x['method'] == 'push_account',
                    AllTypes.get_automation_methods()
                )
            )
            fields = {}
            for tp in platform_types:
                for automation_method in push_account_automation_methods:
                    if tp not in automation_method['type']:
                        continue
                    k = '_'.join(automation_method['type'])
                    if not automation_method['serializer']:
                        continue
                    fields[k] = automation_method['serializer']
                    break

            if not fields:
                serializer_class = default_serializer
            else:
                serializer_class = type('ParamsSerializer', (serializers.Serializer,), fields)
        else:
            serializer_class = default_serializer
        return serializer_class

    @property
    def model_type(self):
        return AutomationTypes.push_account


class PushAccountUpdateAssetSerializer(ChangeSecretUpdateAssetSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateAssetSerializer.Meta.fields


class PushAccountUpdateNodeSerializer(ChangeSecretUpdateNodeSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateNodeSerializer.Meta.fields
