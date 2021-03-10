from common.permissions import IsOrgAdmin
from common.drf.api import JMSBulkRelationModelViewSet, JMSBulkModelViewSet
from ..models import LoginACL
from .. import serializers

__all__ = ['LoginACLViewSet', 'LoginACLUserRelationViewSet']


class LoginACLViewSet(JMSBulkModelViewSet):
    queryset = LoginACL.objects.all()
    filterset_fields = ('name', )
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, )
    serializer_class = serializers.LoginACLSerializer


class LoginACLUserRelationViewSet(JMSBulkRelationModelViewSet):
    m2m_field = LoginACL.users.field
    permission_classes = (IsOrgAdmin,)
    filterset_fields = (
        'id', 'user', 'loginacl'
    )
    search_fields = [
        'id', 'user__name', 'user__username', 'loginacl__name'
    ]
    serializer_class = serializers.LoginACLUserRelationSerializer
