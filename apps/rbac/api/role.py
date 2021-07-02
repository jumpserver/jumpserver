from common.drf.api import JMSModelViewSet
from common.permissions import IsSuperUser, IsOrgAdmin
from ..serializers import RoleSerializer, RoleBindingSerializer
from ..models import Role, RoleBinding

__all__ = ['RoleViewSet', 'RoleBindingViewSet']


class RoleViewSet(JMSModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filterset_fields = ['name', 'scope', 'builtin']
    search_fields = filterset_fields
    permission_classes = (IsSuperUser, )


class RoleBindingViewSet(JMSModelViewSet):
    queryset = RoleBinding.objects.all()
    serializer_class = RoleBindingSerializer
    filterset_fields = ['scope', 'user', 'role', 'org']
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, )
