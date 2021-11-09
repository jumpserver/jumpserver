from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = ['VaultConnectTestSerializer', ]


class VaultConnectTestSerializer(serializers.Serializer):
    VAULT_URL = serializers.CharField(max_length=256, required=True, label='Vault url')
    VAULT_TOKEN = serializers.CharField(
        max_length=256, required=True, label='Vault token', write_only=True
    )
