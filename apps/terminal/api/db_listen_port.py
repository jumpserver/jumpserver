# coding: utf-8
#
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..utils import db_port_manager, DBPortManager
from applications import serializers


db_port_manager: DBPortManager


__all__ = ['DBListenPortViewSet']


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

    @action(methods=['get'], detail=False, url_path='db-info')
    def db_info(self, request, *args, **kwargs):
        port = request.query_params.get("port")
        db = db_port_manager.get_db_by_port(port)
        serializer = serializers.AppSerializer(instance=db)
        return Response(data=serializer.data, status=status.HTTP_200_OK)
