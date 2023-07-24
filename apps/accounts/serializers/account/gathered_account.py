from django.utils.translation import gettext_lazy as _

from accounts.models import GatheredAccount
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .account import AccountAssetSerializer
from .base import BaseAccountSerializer


class GatheredAccountSerializer(BulkOrgResourceModelSerializer):
    asset = AccountAssetSerializer(label=_('Asset'))

    class Meta(BaseAccountSerializer.Meta):
        model = GatheredAccount
        fields = [
            'id', 'present', 'asset', 'username',
            'date_updated', 'address_last_login', 'date_last_login'
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('asset', 'asset__platform')
        return queryset
