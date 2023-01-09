# coding: utf-8
#
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from assets.serializers.asset.database import DatabaseWithGatewaySerializer
from orgs.utils import tmp_to_org
from ..utils import db_port_manager, DBPortManager

db_port_manager: DBPortManager

__all__ = ['DBListenPortViewSet']


class DBListenPortViewSet(GenericViewSet):
    rbac_perms = {
        '*': ['assets.view_asset'],
    }
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        ports = db_port_manager.get_already_use_ports()
        return Response(data=ports, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='db-info')
    def db_info(self, request, *args, **kwargs):
        port = request.query_params.get("port")
        db = db_port_manager.get_db_by_port(port)

        with tmp_to_org(db.org):
            serializer = DatabaseWithGatewaySerializer(instance=db)
            return Response(data=serializer.data, status=status.HTTP_200_OK)
