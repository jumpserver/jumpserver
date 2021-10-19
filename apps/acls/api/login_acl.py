from common.permissions import IsOrgAdmin, HasQueryParamsUserAndIsCurrentOrgMember
from common.drf.api import JMSBulkModelViewSet
from ..models import LoginACL
from .. import serializers
from ..filters import LoginAclFilter

__all__ = ['LoginACLViewSet', ]


class LoginACLViewSet(JMSBulkModelViewSet):
    queryset = LoginACL.objects.all()
    filterset_class = LoginAclFilter
    search_fields = ('name',)
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.LoginACLSerializer

    def get_permissions(self):
        if self.action in ["retrieve", "list"]:
            self.permission_classes = (IsOrgAdmin, HasQueryParamsUserAndIsCurrentOrgMember)
        return super().get_permissions()
