from accounts import serializers
from accounts.models import GatheredAccount
from orgs.mixins.api import OrgBulkModelViewSet

__all__ = [
    'GatheredAccountViewSet',
]


class GatheredAccountViewSet(OrgBulkModelViewSet):
    model = GatheredAccount
    search_fields = ('username', 'asset__address')
    filterset_fields = ('username',)
    serializer_classes = {
        'default': serializers.AccountSerializer,
    }
