from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from common.tree import TreeNodeSerializer
from common.drf.api import JMSModelViewSet
from common.permissions import IsOrgAdmin
from ..models import Permission, Role
from ..serializers import PermissionSerializer

__all__ = ['PermissionViewSet']


class PermissionViewSet(JMSModelViewSet):
    filterset_fields = ['codename']
    serializer_classes = {
        'get_tree': TreeNodeSerializer,
        'default': PermissionSerializer
    }
    permission_classes = (IsOrgAdmin, )

    @action(methods=['GET'], detail=False, url_path='tree')
    def get_tree(self, request, *args, **kwargs):
        show_count = request.query_params.get('show_count', '1') == '1'
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        tree_nodes = Permission.create_tree_nodes(queryset)
        serializer = self.get_serializer(tree_nodes, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        scope = self.request.query_params.get('scope') or 'org'
        role_id = self.request.query_params.get('role')

        if role_id:
            role = get_object_or_404(Role, pk=role_id)
            queryset = role.get_permissions()
        else:
            queryset = Permission.get_permissions(scope)

        queryset = queryset.prefetch_related('content_type')
        return queryset


# class UserPermsApi(ListAPIView):
#     serializer_class = UserPermsSerializer
#     permission_classes = (IsValidUser,)
#
#     def list(self, request, *args, **kwargs):
#         perms = RoleBinding.get_user_perms(request.user)
#         serializer = super().get_serializer(data={'perms': perms})
#         return Res

