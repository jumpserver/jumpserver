from common.api import JMSBulkModelViewSet
from .. import serializers
from ..models import LoginACL
from ..filters import LoginAclFilter

__all__ = ['LoginACLViewSet']


class LoginACLViewSet(JMSBulkModelViewSet):
    queryset = LoginACL.objects.all()
    filterset_class = LoginAclFilter
    search_fields = ('name',)
    serializer_class = serializers.LoginACLSerializer

