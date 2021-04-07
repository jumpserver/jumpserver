from orgs.mixins.api import OrgBulkModelViewSet
from .. import serializers
from ..models import Account
from .mixins import SafeViewSetMixin


__all__ = ['AccountViewSet']


class AccountViewSet(SafeViewSetMixin, OrgBulkModelViewSet):
    serializer_class = serializers.AccountSerializer
    model = Account
    filterset_fields = {
        'id': ['exact', 'in'],
        'name': ['exact'],
        'username': ['exact'],
        'type': ['exact', 'in'],
        'type__name': ['exact', 'in'],
        'address': ['exact'],
        'is_privileged': ['exact'],
        'safe': ['exact', 'in'],
        'safe__name': ['exact']
    }
    search_fields = (
        'id', 'name', 'username', 'type', 'type__name', 'address', 'is_privileged', 'safe',
        'safe__name'
    )
