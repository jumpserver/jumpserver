from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin
from .. import serializers
from ..models import Account


__all__ = ['AccountViewSet']


class AccountViewSet(OrgBulkModelViewSet):
    permission_classes = (IsOrgAdmin, )
    filterset_fields = (
        'name', 'username', 'type', 'type__name', 'address', 'is_privileged', 'safe', 'safe__name'
    )
    search_fields = filterset_fields
    serializer_class = serializers.AccountSerializer
    model = Account
