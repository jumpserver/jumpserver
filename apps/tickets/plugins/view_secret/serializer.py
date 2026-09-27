from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..resources import AssetAccountRequestSerializer
from accounts.const import SecretType


class RequestSerializer(AssetAccountRequestSerializer):
    duration = serializers.IntegerField(min_value=60, max_value=86400, default=600, label=_('Validity (seconds)'))

    def validate(self, attrs):
        from accounts.models import Account
        from orgs.utils import tmp_to_org
        attrs = super().validate(attrs)
        with tmp_to_org(self.context['org_id']):
            names = set(Account.objects.filter(
                asset_id=attrs['asset'], asset__org_id=self.context['org_id'],
                username__in=attrs['accounts'], secret_type=SecretType.PASSWORD, is_active=True,
            ).values_list('username', flat=True))
        if names != set(attrs['accounts']):
            raise serializers.ValidationError({'accounts': _('Select active password accounts.')})
        return attrs
