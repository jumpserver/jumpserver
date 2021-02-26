from orgs.mixins.api import OrgModelViewSet
from common.permissions import IsOrgAdminOrAppUser
from .models import AssetACLPolicy
from .serializers import AssetACLPolicySerializer


class AssetACLViewSet(OrgModelViewSet):
    permission_classes = (IsOrgAdminOrAppUser,)
    model = AssetACLPolicy
    filterset_fields = ("name", 'user', 'ip', 'port', 'system_user')
    search_fields = filterset_fields
    serializer_class = AssetACLPolicySerializer
