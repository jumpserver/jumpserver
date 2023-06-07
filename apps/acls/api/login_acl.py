from common.api import JMSBulkModelViewSet
from .common import ACLUserFilterMixin
from .. import serializers
from ..models import LoginACL

__all__ = ['LoginACLViewSet']


class LoginACLFilter(ACLUserFilterMixin):
    class Meta:
        model = LoginACL
        fields = ('name', 'action')


class LoginACLViewSet(JMSBulkModelViewSet):
    queryset = LoginACL.objects.all()
    filterset_class = LoginACLFilter
    search_fields = ('name',)
    serializer_class = serializers.LoginACLSerializer
