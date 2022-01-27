from common.drf.api import JMSBulkModelViewSet
from ..models import LoginACL
from .. import serializers

__all__ = ['LoginACLViewSet']


class LoginACLViewSet(JMSBulkModelViewSet):
    queryset = LoginACL.objects.all()
    filterset_fields = ('name', 'user', )
    search_fields = filterset_fields
    serializer_class = serializers.LoginACLSerializer
    # Todo: 这里是不是要返回用户自己的 acl

