# coding: utf-8
#
from orgs.mixins.api import OrgBulkModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


from common.tree import TreeNodeSerializer
from common.mixins.api import SuggestionMixin
from ..utils import db_port_manager
from .. import serializers
from ..models import Application

__all__ = ['ApplicationViewSet', 'DBListenPortViewSet']


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


class DBListenPortViewSet(GenericViewSet):
    rbac_perms = {
        'GET': 'applications.view_application',
        'list': 'applications.view_application',
        'db_info': 'applications.view_application',
    }

    http_method_names = ['get', 'post']

    def list(self, request, *args, **kwargs):
        ports = db_port_manager.get_already_use_ports()
        return Response(data=ports, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='db-info')
    def db_info(self, request, *args, **kwargs):
        port = request.data.get("port")
        db, msg = db_port_manager.get_db_by_port(port)
        if db:
            serializer = serializers.AppSerializer(instance=db)
            data = serializer.data
            _status = status.HTTP_200_OK
        else:
            data = {'error': msg}
            _status = status.HTTP_404_NOT_FOUND
        return Response(data=data, status=_status)
