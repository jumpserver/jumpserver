from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import AssetAccountRequestSerializer


class RequestSerializer(AssetAccountRequestSerializer):
    direction = serializers.ChoiceField(choices=[('upload', _('Upload')), ('download', _('Download'))], label=_('Direction'))
    paths = serializers.ListField(child=serializers.CharField(max_length=4096), allow_empty=False,
                                 max_length=100, label=_('File paths'))
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=3600, label=_('Validity (seconds)'))

    invalid_accounts_message = _('Select active accounts with existing access.')

    def get_accounts(self, asset_id):
        from assets.models import Asset
        from .permissions import base_access
        asset = Asset.objects.filter(pk=asset_id, org_id=self.context['org_id'], is_active=True).first()
        access = base_access(self.context['request'].user, asset) if asset else {}
        return super().get_accounts(asset_id).filter(pk__in=access, is_active=True)
