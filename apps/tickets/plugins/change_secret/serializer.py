from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretType
from ..resources import AssetAccountRequestSerializer


class RequestSerializer(AssetAccountRequestSerializer):
    invalid_accounts_message = _('Select active password accounts that allow password changes.')

    def validate_asset(self, value):
        from assets.models import Asset
        value = super().validate_asset(value)
        if not settings.XPACK_LICENSE_IS_VALID:
            raise serializers.ValidationError(_('A valid license is required to change account passwords.'))
        if not Asset.objects.filter(
            pk=value, org_id=self.context['org_id'], is_active=True,
            platform__automation__ansible_enabled=True,
            platform__automation__change_secret_enabled=True,
        ).exclude(platform__automation__change_secret_method__isnull=True).exclude(
            platform__automation__change_secret_method='',
        ).exists():
            raise serializers.ValidationError(_('Enable password changes on the asset platform first.'))
        return value

    def get_accounts(self, asset_id):
        accounts = super().get_accounts(asset_id).filter(
            org_id=self.context['org_id'], is_active=True, secret_reset=True, secret_type=SecretType.PASSWORD,
        )
        if settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED:
            accounts = accounts.filter(privileged=False).exclude(username__in=['root', 'administrator'])
        return accounts
