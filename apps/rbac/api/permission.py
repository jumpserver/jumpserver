from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from common.tree import TreeNodeSerializer
from common.api import JMSModelViewSet
from ..models import Permission, Role
from ..serializers import PermissionSerializer

__all__ = ['PermissionViewSet']


class PermissionViewSet(JMSModelViewSet):
    filterset_fields = ['codename']
    serializer_classes = {
        'get_tree': TreeNodeSerializer,
        'default': PermissionSerializer
    }
    scope = 'org'
    check_disabled = False
    http_method_names = ['get', 'option', 'head']

    @action(methods=['GET'], detail=False, url_path='tree')
    def get_tree(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        tree_nodes = Permission.create_tree_nodes(
            queryset, scope=self.scope, check_disabled=self.check_disabled
        )
        serializer = self.get_serializer(tree_nodes, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        self.scope = self.request.query_params.get('scope') or 'org'
        role_id = self.request.query_params.get('role')

        if role_id:
            role = get_object_or_404(Role, pk=role_id)
            self.scope = role.scope
            queryset = role.get_permissions()
        else:
            queryset = Permission.get_permissions(self.scope)
        queryset = queryset.prefetch_related('content_type')
        return queryset
