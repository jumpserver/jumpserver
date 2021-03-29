from common.permissions import IsOrgAdmin
from orgs.mixins.api import OrgBulkModelViewSet
from ..serializers import SafeSerializer
from ..models import Safe


__all__ = ['SafeViewSet']


class SafeViewSet(OrgBulkModelViewSet):
    model = Safe
    permission_classes = (IsOrgAdmin, )
    serializer_class = SafeSerializer
    filterset_fields = ('name', )
    search_fields = filterset_fields
