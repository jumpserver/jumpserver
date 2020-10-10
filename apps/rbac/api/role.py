from common.permissions import RBACPermission
from rest_framework.viewsets import ModelViewSet

from rbac.models import Role, RoleBinding
from rbac.serializers import RoleSerializer, RoleBindingSerializer


__all__ = ['RoleViewSet', 'RoleBindingViewSet']


class RoleViewSet(ModelViewSet):

    permission_classes = (RBACPermission,)

    filter_fields = ('name', 'type', 'is_build_in')
    search_fields = filter_fields
    ordering_fields = ('type',)

    model = Role
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class RoleBindingViewSet(ModelViewSet):

    permission_classes = (RBACPermission,)

    filter_fields = ('user', 'role')
    search_fields = filter_fields
    ordering_fields = ('role',)

    model = RoleBinding
    queryset = RoleBinding.objects.all()
    serializer_class = RoleBindingSerializer
