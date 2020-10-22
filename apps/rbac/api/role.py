from rest_framework.viewsets import ModelViewSet

from common.permissions import IsSuperUser
from ..models import Role, RoleNamespaceBinding, RoleOrgBinding
from ..serializers import RoleSerializer, RoleNamespaceBindingSerializer, RoleOrgBindingSerializer

__all__ = ['RoleViewSet', 'RoleNamespaceBindingViewSet', 'RoleOrgBindingViewSet']


class RoleViewSet(ModelViewSet):
    permission_classes = (IsSuperUser,)
    filter_fields = ('name', 'type', 'is_build_in')
    search_fields = filter_fields
    ordering_fields = ('type',)
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class RoleNamespaceBindingViewSet(ModelViewSet):
    permission_classes = ()
    filter_fields = ('user', 'role')
    search_fields = filter_fields
    ordering_fields = ('role',)
    queryset = RoleNamespaceBinding.objects.all()
    serializer_class = RoleNamespaceBindingSerializer


class RoleOrgBindingViewSet(ModelViewSet):
    permission_classes = ()
    filter_fields = ('user', 'role')
    search_fields = filter_fields
    ordering_fields = ('role',)
    queryset = RoleOrgBinding.objects.all()
    serializer_class = RoleOrgBindingSerializer
