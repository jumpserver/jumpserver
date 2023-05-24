from common.api import JMSBulkModelViewSet
from .. import serializers
from ..filters import LoginAclFilter
from ..models import LoginACL

__all__ = ['LoginACLViewSet']


class LoginACLViewSet(JMSBulkModelViewSet):
    queryset = LoginACL.objects.all()
    filterset_class = LoginAclFilter
    search_fields = ('name',)
    serializer_class = serializers.LoginACLSerializer
