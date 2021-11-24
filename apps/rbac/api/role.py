from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action

from common.tree import TreeNodeSerializer
from common.drf.api import JMSModelViewSet
from common.permissions import IsSuperUser, IsOrgAdmin
from ..serializers import RoleSerializer, RoleBindingSerializer
from ..models import Role, RoleBinding, Permission
from .permission import PermissionViewSet

__all__ = ['RoleViewSet', 'RoleBindingViewSet', 'RolePermissionsViewSet']


class RoleViewSet(JMSModelViewSet):
    queryset = Role.objects.all()
    serializer_classes = {
        'get_tree': TreeNodeSerializer,
        'default': RoleSerializer
    }
    filterset_fields = ['name', 'scope', 'builtin']
    search_fields = filterset_fields
    permission_classes = (IsSuperUser, )

    @action(methods=['GET'], detail=False, url_path='tree')
    def get_tree(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        tree_nodes = Permission.create_tree_nodes(queryset, scope=self.scope)
        serializer = self.get_serializer(tree_nodes, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        queryset = super().get_queryset()\
            .annotate(users_amount=Count('users')) \
            .annotate(permissions_amount=Count('permissions'))
        return queryset


class RoleBindingViewSet(JMSModelViewSet):
    queryset = RoleBinding.objects.all()
    serializer_class = RoleBindingSerializer
    filterset_fields = ['scope', 'user', 'role', 'org']
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, )


class RolePermissionsViewSet(PermissionViewSet):
    def get_queryset(self):
        print("Kwargs: ", self.kwargs)
        role_id = self.kwargs.get('role_pk')
        print("roleId: ", role_id)
        role = Role.objects.get(id=role_id)
        # role = get_object_or_404(Role, pk=role_id)
        self.scope = role.scope
        queryset = role.get_permissions()\
            .prefetch_related('content_type')
        return queryset
