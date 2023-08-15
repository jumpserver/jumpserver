import uuid

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import VaultTypeChoices
from common.serializers.fields import EncryptedField

__all__ = [
    'AnnouncementSettingSerializer',
    'VaultSettingSerializer', 'TicketSettingSerializer'
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
    ANNOUNCEMENT_ENABLED = serializers.BooleanField(label=_('Enable announcement'), default=True)
    ANNOUNCEMENT = AnnouncementSerializer(label=_("Announcement"))


class VaultSettingSerializer(serializers.Serializer):
    VAULT_TYPE = serializers.ChoiceField(
        default=VaultTypeChoices.local, choices=VaultTypeChoices.choices,
        required=False, label=_('Type')
    )
    VAULT_HCP_HOST = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Host')
    )
    VAULT_HCP_TOKEN = EncryptedField(
        max_length=256, allow_blank=True, required=False, label=_('Token'), default=''
    )
    VAULT_HCP_MOUNT_POINT = serializers.CharField(
        max_length=256, allow_blank=True, required=False, label=_('Mount Point')
    )

    def validate(self, attrs):
        attrs.pop('VAULT_TYPE', None)
        return attrs


class TicketSettingSerializer(serializers.Serializer):
    TICKETS_ENABLED = serializers.BooleanField(required=False, default=True, label=_("Enable tickets"))
    TICKET_AUTHORIZE_DEFAULT_TIME = serializers.IntegerField(
        min_value=1, max_value=999999, required=False,
        label=_("Ticket authorize default time")
    )
    TICKET_AUTHORIZE_DEFAULT_TIME_UNIT = serializers.ChoiceField(
        choices=[('day', _("day")), ('hour', _("hour"))],
        label=_("Ticket authorize default time unit"), required=False,
    )


class OpsSettingSerializer(serializers.Serializer):
    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(
        required=False, label=_('Operation center'),
        help_text=_('Allow user run batch command or not using ansible')
    )
    SECURITY_COMMAND_BLACKLIST = serializers.ListField(
        child=serializers.CharField(max_length=1024, ),
        label=_('Operation center command blacklist'),
        help_text=_("Commands that are not allowed execute.")
    )
