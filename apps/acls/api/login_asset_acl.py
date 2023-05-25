from common.drf.filters import BaseFilterSet
from orgs.mixins.api import OrgBulkModelViewSet
from .common import ACLFiltersetMixin
from .. import models, serializers

__all__ = ['LoginAssetACLViewSet']


class CommandACLFilter(ACLFiltersetMixin, BaseFilterSet):
    class Meta:
        model = models.LoginAssetACL
        fields = ['name', 'users', 'assets']


class LoginAssetACLViewSet(OrgBulkModelViewSet):
    model = models.LoginAssetACL
    filterset_class = CommandACLFilter
    search_fields = ['name']
    serializer_class = serializers.LoginAssetACLSerializer
