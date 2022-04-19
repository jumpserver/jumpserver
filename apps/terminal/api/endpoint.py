from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from common.drf.api import JMSBulkModelViewSet
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from assets.models import Asset
from orgs.utils import tmp_to_root_org
from applications.models import Application
from terminal.models import Session
from common.permissions import IsValidUser
from ..models import Endpoint, EndpointRule
from .. import serializers


__all__ = ['EndpointViewSet', 'EndpointRuleViewSet']


class EndpointViewSet(JMSBulkModelViewSet):
    filterset_fields = ('name', 'host')
    search_fields = filterset_fields
    serializer_class = serializers.EndpointSerializer
    queryset = Endpoint.objects.all()

    @staticmethod
    def get_target_ip(request):
        # 用来方便测试
        target_ip = request.GET.get('target_ip')
        if target_ip:
            return target_ip

        asset_id = request.GET.get('asset_id')
        app_id = request.GET.get('app_id')
        session_id = request.GET.get('session_id')
        token = request.GET.get('token')
        if token:
            from authentication.api.connection_token import TokenCacheMixin as TokenUtil
            value = TokenUtil().get_token_from_cache(token)
            if value:
                if value.get('type') == 'asset':
                    asset_id = value.get('asset')
                else:
                    app_id = value.get('application')
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

    @action(methods=['get'], detail=False, permission_classes=[IsValidUser], url_path='smart')
    def smart(self, request, *args, **kwargs):
        protocol = request.GET.get('protocol')
        if not protocol:
            return Response(
                data={'error': _('Not found protocol query params')},
                status=status.HTTP_404_NOT_FOUND
            )
        target_ip = self.get_target_ip(request)
        endpoint = EndpointRule.match_endpoint(target_ip, protocol, request)
        serializer = self.get_serializer(endpoint)
        return Response(serializer.data)


class EndpointRuleViewSet(JMSBulkModelViewSet):
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.EndpointRuleSerializer
    queryset = EndpointRule.objects.all()
