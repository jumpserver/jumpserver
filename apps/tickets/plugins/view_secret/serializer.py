from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import AssetAccountRequestSerializer
from accounts.const import SecretType


class RequestSerializer(AssetAccountRequestSerializer):
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=600, label=_('Validity (seconds)'))

    invalid_accounts_message = _('Select active password accounts.')

    def get_accounts(self, asset_id):
        return super().get_accounts(asset_id).filter(secret_type=SecretType.PASSWORD, is_active=True)
