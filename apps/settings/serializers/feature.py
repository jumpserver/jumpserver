import uuid

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import VaultTypeChoices
from assets.const import Protocol
from common.serializers.fields import EncryptedField

__all__ = [
    'AnnouncementSettingSerializer', 'OpsSettingSerializer', 'VaultSettingSerializer',
    'HashicorpKVSerializer', 'AzureKVSerializer', 'TicketSettingSerializer',
    'ChatAISettingSerializer', 'VirtualAppSerializer',
]


class AnnouncementSerializer(serializers.Serializer):
    ID = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    SUBJECT = serializers.CharField(required=True, max_length=1024, label=_("Subject"))
    CONTENT = serializers.CharField(label=_("Content"))
    LINK = serializers.URLField(
        required=False, allow_null=True, allow_blank=True,
        label=_("More url"), default='',
    )

    def to_representation(self, instance):
        defaults = {'ID': '', 'SUBJECT': '', 'CONTENT': '', 'LINK': '', 'ENABLED': False}
        data = {**defaults, **instance}
        return super().to_representation(data)

    def to_internal_value(self, data):
        data['ID'] = str(uuid.uuid4())
        return super().to_internal_value(data)


class AnnouncementSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Announcement')

    ANNOUNCEMENT_ENABLED = serializers.BooleanField(label=_('Enable announcement'), default=True)
    ANNOUNCEMENT = AnnouncementSerializer(label=_("Announcement"))


class VaultSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Vault')

    VAULT_ENABLED = serializers.BooleanField(
        required=False, label=_('Enable Vault'), read_only=True
    )
    VAULT_BACKEND = serializers.ChoiceField(
        choices=VaultTypeChoices.choices, default=VaultTypeChoices.local, label=_('Vault provider')
    )

    HISTORY_ACCOUNT_CLEAN_LIMIT = serializers.IntegerField(
        default=999, max_value=999, min_value=1,
        required=False, label=_('Historical accounts retained count'),
        help_text=_(
            'If the specific value is less than 999, '
            'the system will automatically perform a task every night: '
            'check and delete historical accounts that exceed the predetermined number. '
            'If the value reaches or exceeds 999, no historical account deletion will be performed.'
        )
    )


class HashicorpKVSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Vault')
    VAULT_HCP_HOST = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Host')
    )
    VAULT_HCP_TOKEN = EncryptedField(
        max_length=256, allow_blank=True, required=False, label=_('Token'), default=''
    )
    VAULT_HCP_MOUNT_POINT = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Mount Point')
    )


class AzureKVSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Vault')
    VAULT_AZURE_HOST = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Host')
    )
    VAULT_AZURE_CLIENT_ID = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Client ID')
    )
    VAULT_AZURE_CLIENT_SECRET = EncryptedField(
        max_length=4096, allow_blank=True, required=False, label=_('Client Secret'), default=''
    )
    VAULT_AZURE_TENANT_ID = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Tenant ID')
    )


class ChatAISettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Chat AI')
    API_MODEL = Protocol.gpt_protocols()[Protocol.chatgpt]['setting']['api_mode']
    GPT_MODEL_CHOICES = API_MODEL['choices']
    GPT_MODEL_DEFAULT = API_MODEL['default']

    CHAT_AI_ENABLED = serializers.BooleanField(
        required=False, label=_('Enable Chat AI')
    )
    GPT_BASE_URL = serializers.CharField(
        allow_blank=True, required=False, label=_('Base Url')
    )
    GPT_API_KEY = EncryptedField(
        allow_blank=True, required=False, label=_('API Key'),
    )
    GPT_PROXY = serializers.CharField(
        allow_blank=True, required=False, label=_('Proxy')
    )
    GPT_MODEL = serializers.ChoiceField(
        default=GPT_MODEL_DEFAULT, choices=GPT_MODEL_CHOICES, label=_("GPT Model"), required=False,
    )


class TicketSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Ticket')

    TICKETS_ENABLED = serializers.BooleanField(required=False, default=True, label=_("Enable tickets"))
    TICKETS_DIRECT_APPROVE = serializers.BooleanField(required=False, default=False, label=_("No login approval"))
    TICKET_AUTHORIZE_DEFAULT_TIME = serializers.IntegerField(
        min_value=1, max_value=999999, required=False,
        label=_("Ticket authorize default time")
    )
    TICKET_AUTHORIZE_DEFAULT_TIME_UNIT = serializers.ChoiceField(
        choices=[('day', _("day")), ('hour', _("hour"))],
        label=_("Ticket authorize default time unit"), required=False,
    )


class OpsSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Feature')

    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(
        required=False, label=_('Operation center'),
        help_text=_('Allow user run batch command or not using ansible')
    )
    SECURITY_COMMAND_BLACKLIST = serializers.ListField(
        child=serializers.CharField(max_length=1024, ),
        label=_('Operation center command blacklist'),
        help_text=_("Commands that are not allowed execute.")
    )


class VirtualAppSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Virtual app')

    VIRTUAL_APP_ENABLED = serializers.BooleanField(
        required=False, label=_('Enable virtual app'),
    )
