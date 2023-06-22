from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from accounts.const import VaultType
from common.serializers.fields import EncryptedField

__all__ = ['VaultSettingSerializer']


class VaultSettingSerializer(serializers.Serializer):
    HCP_VAULT_MOUNT_POINT = serializers.CharField(max_length=256, required=False, label=_('HCP Vault mount point'))
    HCP_VAULT_HOST = serializers.CharField(max_length=256, required=False, label=_('HCP Vault host'))
    HCP_VAULT_TOKEN = EncryptedField(max_length=256, required=False, label=_('HCP Vault token'))
    VAULT_TYPE = serializers.ChoiceField(
        default=VaultType.LOCAL, choices=VaultType.choices,
        required=False, label=_('Vault type')
    )