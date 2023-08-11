from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import VaultTypeChoices
from common.serializers.fields import EncryptedField

__all__ = ['VaultSettingSerializer']


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
