from orgs.mixins.api import OrgBulkModelViewSet

from .common import ACLUserAssetFilterMixin
from .. import models, serializers

__all__ = ['ClipboardACLViewSet']


class ClipboardACLFilter(ACLUserAssetFilterMixin):
    class Meta:
        model = models.ClipboardACL
        fields = ['name', 'users', 'assets', 'action']


class ClipboardACLViewSet(OrgBulkModelViewSet):
    model = models.ClipboardACL
    filterset_class = ClipboardACLFilter
    search_fields = ['name']
    serializer_class = serializers.ClipboardACLSerializer
