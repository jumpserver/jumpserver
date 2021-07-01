from common.drf.api import JMSModelViewSet
from common.permissions import IsOrgAdmin
from ..models import Permission
from ..serializers import PermissionSerializer

__all__ = ['PermissionViewSet']


class PermissionViewSet(JMSModelViewSet):
    filterset_fields = ['codename']
    serializer_class = PermissionSerializer
    permission_classes = (IsOrgAdmin, )

    def get_queryset(self):
        scope = self.request.query_params.get('scope')
        return Permission.get_permissions(scope)
