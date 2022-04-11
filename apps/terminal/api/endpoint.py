from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from common.drf.api import JMSBulkModelViewSet
from common.utils import get_object_or_none
from django.shortcuts import get_object_or_404
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
        'smart': 'terminal.view_endpoint'
    }

    @staticmethod
    def get_target_ip(request):
        target_ip = request.GET.get('target_ip')
        if target_ip:
            return target_ip
        asset_id = request.GET.get('asset_id')
        app_id = request.GET.get('app_id')
        session_id = request.GET.get('session_id')
        if asset_id:
            pk, model = asset_id, Asset
        elif app_id:
            pk, model = app_id, Application
        elif session_id:
            pk, model = session_id, Session
        else:
            return ''

        with tmp_to_root_org():
            instance = get_object_or_404(model, pk=pk)
            target_ip = instance.get_target_ip()
            return target_ip

    @action(methods=['get'], detail=False, url_path='smart')
    def smart(self, request, *args, **kwargs):
        protocol = request.GET.get('protocol')
        if not protocol:
            return Response(
                data={'error': _('Not found protocol query params')},
                status=status.HTTP_404_NOT_FOUND
            )
        target_ip = self.get_target_ip(request)
        serializer = serializers.SmartEndpointSerializer(
            data={'match_protocol': protocol, 'match_target_ip': target_ip},
            context=self.get_serializer_context()
        )
        serializer.is_valid()
        return Response(serializer.data)


class EndpointRuleViewSet(JMSBulkModelViewSet):
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.EndpointRuleSerializer
    queryset = EndpointRule.objects.all()
