from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin
from .. import serializers


__all__ = ['AccountViewSet']


class AccountViewSet(OrgBulkModelViewSet):
    permission_classes = (IsOrgAdmin, )
    filterset_fields = ('name', 'username', 'type', 'address', 'is_privileged', 'safe')
    search_fields = filterset_fields
    serializer_class = serializers.AccountSerializer
