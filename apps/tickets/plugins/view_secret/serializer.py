from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import AssetAccountRequestSerializer
from accounts.const import SecretType


class RequestSerializer(AssetAccountRequestSerializer):
    asset = serializers.UUIDField(required=False, label=_('Asset'), style={'resource': 'asset'})
    accounts = serializers.ListField(child=serializers.CharField(max_length=128), required=False,
                                    max_length=100, label=_('Accounts'),
                                    style={'resource': 'account', 'depends_on': 'asset'})
    resource_description = serializers.CharField(required=False, max_length=4096, write_only=True,
                                                label=_('Purpose and resource description'))
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=600, label=_('Validity (seconds)'))

    invalid_accounts_message = _('Select active password accounts.')

    def get_accounts(self, asset_id):
        return super().get_accounts(asset_id).filter(secret_type=SecretType.PASSWORD, is_active=True)

    def validate(self, attrs):
        from tickets.plugins import get_ticket_plugin
        from tickets.workflow.resources import validate_description
        plugin = get_ticket_plugin('view_secret')
        validate_description(plugin, attrs, self.context)
        if plugin.resources_pending(attrs):
            return attrs
        return super().validate(attrs)


class ResourceSerializer(AssetAccountRequestSerializer):
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=600, label=_('Validity (seconds)'))
    invalid_accounts_message = _('Select active password accounts.')

    def validate_asset(self, value):
        from assets.models import Asset
        if not Asset.objects.filter(pk=value, org_id=self.context['org_id'], is_active=True).exists():
            raise serializers.ValidationError(_('Resources must belong to the selected organization.'))
        return value

    def get_accounts(self, asset_id):
        return super().get_accounts(asset_id).filter(secret_type=SecretType.PASSWORD, is_active=True)
