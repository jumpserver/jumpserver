from orgs.mixins.api import OrgBulkModelViewSet

from common.permissions import IsOrgAdmin
from .models import AccessControl
from .serializers import LoginPolicySerializer


class LoginPolicyViewSet(OrgBulkModelViewSet):
    model = AccessControl
    serializer_class = LoginPolicySerializer
    permission_classes = (IsOrgAdmin,)
