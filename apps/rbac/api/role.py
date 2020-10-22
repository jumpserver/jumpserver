from rest_framework.viewsets import ModelViewSet

from common.permissions import IsSuperUser
from ..models import Role, NamespaceRoleBinding, OrgRoleBinding
from ..serializers import RoleSerializer, RoleNamespaceBindingSerializer, RoleOrgBindingSerializer

__all__ = ['RoleViewSet', 'NamespaceRoleBindingViewSet', 'OrgRoleBindingViewSet']


class RoleViewSet(ModelViewSet):
    permission_classes = (IsSuperUser,)
    filter_fields = ('name', 'type', 'is_build_in')
    search_fields = filter_fields
    ordering_fields = ('type',)
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class NamespaceRoleBindingViewSet(ModelViewSet):
    permission_classes = ()
    filter_fields = ('user', 'role')
    search_fields = filter_fields
    ordering_fields = ('role',)
    queryset = NamespaceRoleBinding.objects.all()
    serializer_class = RoleNamespaceBindingSerializer


class OrgRoleBindingViewSet(ModelViewSet):
    permission_classes = ()
    filter_fields = ('user', 'role')
    search_fields = filter_fields
    ordering_fields = ('role',)
    queryset = OrgRoleBinding.objects.all()
    serializer_class = RoleOrgBindingSerializer
