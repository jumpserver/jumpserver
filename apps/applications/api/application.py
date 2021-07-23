# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from common.tree import TreeNodeSerializer
from ..hands import IsOrgAdminOrAppUser
from .. import serializers
from ..models import Application
from ..filters import ApplicationFilter


__all__ = ['ApplicationViewSet']


class ApplicationViewSet(OrgBulkModelViewSet):
    model = Application
    filterset_class = ApplicationFilter
    search_fields = ('name', 'type', 'category')
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_classes = {
        'default': serializers.ApplicationSerializer,
        'get_tree': TreeNodeSerializer
    }

    @action(methods=['GET'], detail=False, url_path='tree')
    def get_tree(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        tree_nodes = Application.create_tree_nodes(queryset)
        serializer = self.get_serializer(tree_nodes, many=True)
        return Response(serializer.data)
