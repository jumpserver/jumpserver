from orgs.mixins.api import OrgBulkModelViewSet
from .common import ACLUserAssetFilterMixin
from .. import models, serializers

__all__ = ['LoginAssetACLViewSet']


class LoginAssetACLFilter(ACLUserAssetFilterMixin):
    class Meta:
        model = models.LoginAssetACL
        fields = ['name', ]


class LoginAssetACLViewSet(OrgBulkModelViewSet):
    model = models.LoginAssetACL
    filterset_class = LoginAssetACLFilter
    search_fields = ['name']
    serializer_class = serializers.LoginAssetACLSerializer
