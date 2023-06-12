from common.api import JMSBulkModelViewSet

from orgs.utils import tmp_to_root_org
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

    def filter_queryset(self, queryset):
        with tmp_to_root_org():
            return super().filter_queryset(queryset)

