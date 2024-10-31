from django.utils.translation import gettext_lazy as _

from accounts.models import GatheredAccount
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .account import AccountAssetSerializer as _AccountAssetSerializer
from .base import BaseAccountSerializer

__all__ = [
    'GatheredAccountSerializer',
    'GatheredAccountActionSerializer',
]


class AccountAssetSerializer(_AccountAssetSerializer):
    class Meta(_AccountAssetSerializer.Meta):
        fields = [f for f in _AccountAssetSerializer.Meta.fields if f != 'auto_config']


class GatheredAccountSerializer(BulkOrgResourceModelSerializer):
    asset = AccountAssetSerializer(label=_('Asset'))

    class Meta(BaseAccountSerializer.Meta):
        model = GatheredAccount
        fields = [
            'id', 'present', 'asset', 'username',
            'date_updated', 'address_last_login',
            'groups', 'sudoers', 'authorized_keys',
            'date_last_login', 'status'
        ]
        read_only_fields = fields

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('asset', 'asset__platform')
        return queryset


class GatheredAccountActionSerializer(GatheredAccountSerializer):
    class Meta(GatheredAccountSerializer.Meta):
        read_only_fields = list(set(GatheredAccountSerializer.Meta.read_only_fields) - {'status'})
