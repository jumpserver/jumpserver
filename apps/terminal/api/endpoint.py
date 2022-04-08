from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from common.drf.api import JMSBulkModelViewSet
from common.utils import get_object_or_none
from assets.models import Asset
from orgs.utils import tmp_to_root_org
from applications.models import Application
from terminal.models import Session
from ..models import Endpoint, EndpointRule
from .. import serializers


__all__ = ['EndpointViewSet', 'EndpointRuleViewSet']


class EndpointViewSet(JMSBulkModelViewSet):
    filterset_fields = ('name', 'host')
    search_fields = filterset_fields
    serializer_class = serializers.EndpointSerializer
    queryset = Endpoint.objects.all()
    rbac_perms = {
        'get_connect_url': 'terminal.view_endpoint'
    }

    @action(methods=['get'], detail=False, url_path='connect-url')
    def get_connect_url(self, request, *args, **kwargs):
        protocol = request.GET.get('protocol', 'https')
        asset_id = request.GET.get('asset_id')
        application_id = request.GET.get('application_id')
        session_id = request.GET.get('session_id')
        if asset_id:
            instance_id = asset_id
            model = Asset
        elif application_id:
            instance_id = application_id
            model = Application
        elif session_id:
            instance_id = session_id
            model = Session
        else:
            resp = Response(data={'error': 'Not found instance'}, status=status.HTTP_404_NOT_FOUND)
            return resp

        with tmp_to_root_org():
            instance = get_object_or_none(model, pk=instance_id)
            target_ip = instance.get_target_ip()

        default_host = request.get_host().split(':')[0]
        default_port = 80
        default_data = {
            'host': default_host,
            'port': default_port,
            'url': f'{default_host}:{default_port}'
        }
        data = EndpointRule.get_endpoint_data(target_ip, protocol, default=default_data)
        return Response(data)


class EndpointRuleViewSet(JMSBulkModelViewSet):
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.EndpointRuleSerializer
    queryset = EndpointRule.objects.all()
