# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from common.tree import TreeNodeSerializer
from ..hands import IsOrgAdminOrAppUser, IsValidUser
from .. import serializers
from ..models import Application

__all__ = ['ApplicationViewSet']


class ApplicationViewSet(OrgBulkModelViewSet):
    model = Application
    filterset_fields = {
        'name': ['exact'],
        'category': ['exact'],
        'type': ['exact', 'in'],
    }
    search_fields = ('name', 'type', 'category')
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_classes = {
        'default': serializers.AppSerializer,
        'get_tree': TreeNodeSerializer
    }

    @action(methods=['GET'], detail=False, url_path='tree')
    def get_tree(self, request, *args, **kwargs):
        show_count = request.query_params.get('show_count', '1') == '1'
        queryset = self.filter_queryset(self.get_queryset())
        tree_nodes = Application.create_tree_nodes(queryset, show_count=show_count)
        serializer = self.get_serializer(tree_nodes, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=False, permission_classes=(IsValidUser,))
    def suggestion(self, request):
        queryset = self.filter_queryset(self.get_queryset())[:3]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
