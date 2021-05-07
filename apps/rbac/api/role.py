from common.drf.api import JMSBulkModelViewSet
from common.permissions import IsSuperUser
from ..permissions import IsNotBuiltIn
from .. import serializers
from ..models import Role


__all__ = ['RoleViewSet']


class RoleViewSet(JMSBulkModelViewSet):
    permission_classes = (IsSuperUser, IsNotBuiltIn)
    serializer_class = serializers.RoleSerializer
    filterset_fields = ('display_name', 'name', 'type', 'is_builtin')
    search_fields = filterset_fields
    queryset = Role.objects.all()
