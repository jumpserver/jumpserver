
from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin
from .. import models, serializers


__all__ = ['LoginAssetACLViewSet']


class LoginAssetACLViewSet(OrgBulkModelViewSet):
    model = models.LoginAssetACL
    filterset_fields = ('name', )
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, )
    serializer_class = serializers.LoginAssetACLSerializer
