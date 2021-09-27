from common.permissions import IsOrgAdmin
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
