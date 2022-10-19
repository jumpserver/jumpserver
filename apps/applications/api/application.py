# coding: utf-8
#
from orgs.mixins.api import OrgBulkModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response


from common.tree import TreeNodeSerializer
from common.mixins.api import SuggestionMixin
from .. import serializers
from ..models import Application

__all__ = ['ApplicationViewSet']


class ApplicationViewSet(SuggestionMixin, OrgBulkModelViewSet):
    model = Application
    filterset_fields = {
        'name': ['exact'],
        'category': ['exact', 'in'],
        'type': ['exact', 'in'],
    }
    search_fields = ('name', 'type', 'category')
    serializer_classes = {
        'default': serializers.AppSerializer,
        'get_tree': TreeNodeSerializer,
        'suggestion': serializers.MiniAppSerializer
    }
    rbac_perms = {
        'get_tree': 'applications.view_application',
        'match': 'applications.match_application'
    }

    @action(methods=['GET'], detail=False, url_path='tree')
    def get_tree(self, request, *args, **kwargs):
        show_count = request.query_params.get('show_count', '1') == '1'
        queryset = self.filter_queryset(self.get_queryset())
        tree_nodes = Application.create_tree_nodes(queryset, show_count=show_count)
        serializer = self.get_serializer(tree_nodes, many=True)
        return Response(serializer.data)
