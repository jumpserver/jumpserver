from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from accounts.const import ApplicationCommandEvent

__all__ = ['ApplicationCommandSerializer', 'ApplicationCommandPollSerializer', 'ApplicationCommandResultSerializer']


class ApplicationCommandSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=[
        ApplicationCommandEvent.ACCOUNT_SWITCH_REQUESTED, ApplicationCommandEvent.APPLICATION_RESTART_REQUESTED,
    ])
    client_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=1000)
    credential_id = serializers.UUIDField(required=False)
    timeout_minutes = serializers.IntegerField(min_value=1, max_value=1440, default=30)

    def validate(self, attrs):
        if attrs['event'] == ApplicationCommandEvent.ACCOUNT_SWITCH_REQUESTED and not attrs.get('credential_id'):
            raise serializers.ValidationError({'credential_id': _('Select an account rotation policy.')})
        return attrs


class ApplicationCommandPollSerializer(serializers.Serializer):
    instance_id = serializers.CharField(max_length=128, required=False)


class ApplicationCommandResultSerializer(ApplicationCommandPollSerializer):
    command_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=['running', 'success', 'failed'])
    error_code = serializers.RegexField(r'^[a-zA-Z0-9_.-]*$', max_length=64, required=False, default='', allow_blank=True)
