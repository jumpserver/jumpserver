from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField

__all__ = ['SlackSettingSerializer']


class SlackSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Slack')

    AUTH_SLACK = serializers.BooleanField(default=False, label=_('Slack'))
    SLACK_CLIENT_ID = serializers.CharField(max_length=256, required=True, label='Client ID')
    SLACK_CLIENT_SECRET = EncryptedField(max_length=256, required=False, label='Client Secret')
    SLACK_BOT_TOKEN = EncryptedField(max_length=256, required=False, label='Client bot Token')
    SLACK_RENAME_ATTRIBUTES = serializers.JSONField(
        required=False, label=_('User attribute'),
        help_text=_(
            'User attribute mapping, where the `key` is the JumpServer user attribute name and the '
            '`value` is the Slack service user attribute name'
        )
    )
