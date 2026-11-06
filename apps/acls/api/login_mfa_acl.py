from common.api import JMSBulkModelViewSet

from orgs.utils import tmp_to_root_org
from .common import ACLUserFilterMixin
from .. import serializers
from ..models import LoginMFAACL

__all__ = ['LoginMFAACLViewSet']


class LoginMFAACLFilter(ACLUserFilterMixin):
    class Meta:
        model = LoginMFAACL
        fields = ('name', 'action', 'mfa_type')


class LoginMFAACLViewSet(JMSBulkModelViewSet):
    queryset = LoginMFAACL.objects.all()
    filterset_class = LoginMFAACLFilter
    search_fields = ('name', 'action', 'mfa_type')
    serializer_class = serializers.LoginMFAACLSerializer

    def filter_queryset(self, queryset):
        with tmp_to_root_org():
            return super().filter_queryset(queryset)

