from orgs.mixins.api import OrgBulkModelViewSet
from .. import models, serializers


__all__ = ['CommandFilterACLViewSet']


class CommandFilterACLViewSet(OrgBulkModelViewSet):
    model = models.CommandFilterACL
    filterset_fields = ('name', )
    search_fields = filterset_fields
    serializer_class = serializers.LoginAssetACLSerializer
