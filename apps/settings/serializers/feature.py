import uuid

from django.core.validators import URLValidator
from django.utils import timezone
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from common.utils import date_expired_default
from ops.ansible.docker import ANSIBLE_EE_IMAGE

__all__ = [
    'AnnouncementSettingSerializer', 'OpsSettingSerializer', 'VaultSettingSerializer',
    'OpenBaoSerializer', 'HashicorpKVSerializer', 'AzureKVSerializer', 'TicketSettingSerializer',
    'ChatAISettingSerializer', 'VirtualAppSerializer', 'AmazonSMSerializer',
]


ANSIBLE_DOCKER_HELP_TEXT = lazy(
    lambda: _(
        'Run Ansible jobs in the Docker execution environment (%(image)s). '
        'To run jobs locally instead, disable "Docker isolation for Ansible" under '
        'System Settings > Feature Settings > Job Center. '
        'If the image is missing, run this command on the Ansible worker: '
        'docker pull %(image)s'
    ) % {'image': ANSIBLE_EE_IMAGE},
    str,
)()


class AnnouncementSerializer(serializers.Serializer):
    ID = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    SUBJECT = serializers.CharField(required=True, max_length=1024, label=_("Subject"))
    CONTENT = serializers.CharField(label=_("Content"))
    LINK = serializers.URLField(
        required=False, allow_null=True, allow_blank=True,
        label=_("More Link"), default='',
    )
    DATE_START = serializers.DateTimeField(default=timezone.now, label=_("Date start"))
    DATE_END = serializers.DateTimeField(default=date_expired_default, label=_("Date end"))

    def to_representation(self, instance):
        defaults = {'ID': '', 'SUBJECT': '', 'CONTENT': '', 'LINK': '', 'ENABLED': False}
        data = {**defaults, **instance}
        return super().to_representation(data)

    def to_internal_value(self, data):
        data['ID'] = str(uuid.uuid4())
        return super().to_internal_value(data)


class AnnouncementSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Announcement')

    ANNOUNCEMENT_ENABLED = serializers.BooleanField(label=_('Announcement'), default=True)
    ANNOUNCEMENT = AnnouncementSerializer(label=_("Announcement"))


class BaseVaultSettingSerializer(serializers.Serializer):

    def post_save(self):
        from accounts.signal_handlers import vault_pub_sub
        vault_pub_sub.publish('vault')


class VaultSettingSerializer(BaseVaultSettingSerializer, serializers.Serializer):
    PREFIX_TITLE = _('Vault')

    VAULT_ENABLED = serializers.BooleanField(
        required=False, label=_('Vault'), read_only=True
    )
    VAULT_BACKEND = serializers.CharField(
        max_length=16, required=False, label=_('Vault provider'), read_only=True
    )
    HISTORY_ACCOUNT_CLEAN_LIMIT = serializers.IntegerField(
        default=999, max_value=999, min_value=1,
        required=False, label=_('Record limit'),
        help_text=_(
            'If the specific value is less than 999 (default), '
            'the system will automatically perform a task every night: '
            'check and delete historical accounts that exceed the predetermined number. '
            'If the value reaches or exceeds 999 (default), '
            'no historical account deletion will be performed'
        )
    )


class OpenBaoSerializer(BaseVaultSettingSerializer, serializers.Serializer):
    PREFIX_TITLE = _('OpenBao')
    VAULT_OPENBAO_ADDR = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('OpenBao address')
    )
    VAULT_OPENBAO_TOKEN = EncryptedField(
        max_length=4096, allow_blank=True, required=False, label=_('Token'), default=''
    )
    VAULT_OPENBAO_MOUNT_POINT = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Mount Point')
    )
    VAULT_OPENBAO_TIMEOUT = serializers.IntegerField(
        max_value=120, min_value=1, required=False, label=_('Timeout')
    )


class HashicorpKVSerializer(BaseVaultSettingSerializer, serializers.Serializer):
    PREFIX_TITLE = _('HCP Vault')
    VAULT_HCP_HOST = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Host')
    )
    VAULT_HCP_TOKEN = EncryptedField(
        max_length=256, allow_blank=True, required=False, label=_('Token'), default=''
    )
    VAULT_HCP_MOUNT_POINT = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Mount Point')
    )


class AzureKVSerializer(BaseVaultSettingSerializer, serializers.Serializer):
    PREFIX_TITLE = _('Azure Key Vault')
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


class AmazonSMSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Amazon Secrets Manager')
    VAULT_AWS_REGION_NAME = serializers.CharField(
        max_length=256, required=True, label=_('Region')
    )
    VAULT_AWS_ACCESS_KEY_ID = serializers.CharField(
        max_length=1024, required=True, label=_('Access key ID')
    )
    VAULT_AWS_ACCESS_SECRET_KEY = EncryptedField(
        max_length=1024, required=False, allow_blank=True,
        label=_('Access key secret'), default=''
    )


class ChatAISettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Chat AI')

    CHAT_AI_ENABLED = serializers.BooleanField(
        required=False, label=_('Chat AI')
    )
    CHAT_AI_METHOD = serializers.ChoiceField(
        choices=(('api', _('Built-in API')), ('iframe', _('iframe embed'))),
        default='api', required=False, label=_('Method'),
    )
    CHAT_AI_EMBED_URL = serializers.URLField(
        allow_blank=True, required=False, label=_('iframe URL'),
        help_text=_('The page URL loaded in the isolated AI assistant iframe.'),
        validators=[URLValidator(schemes=('http', 'https'))],
    )
    CHAT_AI_BASE_URL = serializers.CharField(
        allow_blank=True, required=False, label=_('Base URL'),
        help_text=_('OpenAI-compatible API base URL, usually ending in /v1.')
    )
    CHAT_AI_API_KEY = EncryptedField(
        allow_blank=True, required=False, label=_('API Key'),
    )
    CHAT_AI_PROXY = serializers.CharField(
        allow_blank=True, required=False, label=_('Proxy'),
        help_text=_('HTTP proxy used to reach the model provider. For example: http://ip:port')
    )
    CHAT_AI_MODEL = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Model'),
        help_text=_('Discover models from the provider or enter a model ID manually.')
    )
    CHAT_AI_VOICE_TRANSCRIPTION_MODE = serializers.ChoiceField(
        choices=(('browser', _('Browser speech recognition')), ('server', _('Server transcription'))),
        required=False, label=_('Voice transcription mode'),
        help_text=_('Use browser speech recognition or upload audio to the configured server provider.'),
    )
    CHAT_AI_WEB_SEARCH_ENABLED = serializers.BooleanField(
        required=False, label=_('Web search')
    )
    CHAT_AI_WEB_SEARCH_PROVIDER = serializers.ChoiceField(
        choices=(('tavily', 'Tavily'), ('searxng', 'SearXNG')),
        required=False, label=_('Web search provider'),
    )
    CHAT_AI_WEB_SEARCH_BASE_URL = serializers.CharField(
        allow_blank=True, required=False, label=_('Web search base URL'),
        help_text=_(
            'Tavily API or SearXNG base URL. SearXNG must enable JSON responses.'
        ),
    )
    CHAT_AI_WEB_SEARCH_API_KEY = EncryptedField(
        allow_blank=True, required=False, label=_('Web search API key'),
        help_text=_('Used only by Tavily. It is never sent to SearXNG.'),
    )
    CHAT_AI_WEB_SEARCH_PROXY = serializers.CharField(
        allow_blank=True, required=False, label=_('Web search proxy'),
        help_text=_('HTTP proxy used only for public web searches.'),
    )
class TicketSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Ticket')

    TICKETS_ENABLED = serializers.BooleanField(required=False, default=True, label=_("Ticket"))
    TICKETS_DIRECT_APPROVE = serializers.BooleanField(
        required=False, default=False, label=_("Approval without login"),
        help_text=_('Allow direct approval ticket without login')
    )
    TICKET_AUTHORIZE_DEFAULT_TIME = serializers.IntegerField(
        min_value=1, max_value=999999, required=False,
        label=_("Period"),
        help_text=_("The default authorization time period when applying for assets via a ticket")
    )
    TICKET_AUTHORIZE_DEFAULT_TIME_UNIT = serializers.ChoiceField(
        choices=[('day', _("day")), ('hour', _("hour"))],
        label=_("Unit"), required=False, help_text=_("The unit of period")
    )


class OpsSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Feature')

    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(
        required=False, label=_('Job Center'),
        help_text=_('Allow users to use the Job Center to execute jobs')
    )
    ANSIBLE_DOCKER_ENABLED = serializers.BooleanField(
        required=False,
        label=_('Docker isolation for Ansible'),
        help_text=ANSIBLE_DOCKER_HELP_TEXT,
    )
    SECURITY_COMMAND_BLACKLIST = serializers.ListField(
        child=serializers.CharField(max_length=1024),
        label=_('Command blacklist'),
        help_text=_("Command blacklist in Adhoc"),
        default=list,
    )


class VirtualAppSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Virtual app')

    VIRTUAL_APP_ENABLED = serializers.BooleanField(
        required=False, label=_('Virtual App'),
        help_text=_(
            'Virtual applications, you can use the Linux operating system as an application server '
            'in remote applications.'
        )
    )
