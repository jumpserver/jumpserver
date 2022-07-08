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


class SmartEndpointViewMixin:
    get_serializer: callable

    @action(methods=['get'], detail=False, permission_classes=[IsValidUser], url_path='smart')
    def smart(self, request, *args, **kwargs):
        protocol = request.GET.get('protocol')
        if not protocol:
            error = _('Not found protocol query params')
            return Response(data={'error': error}, status=status.HTTP_404_NOT_FOUND)
        endpoint = self.match_endpoint(request, protocol)
        serializer = self.get_serializer(endpoint)
        return Response(serializer.data)

    def match_endpoint(self, request, protocol):
        instance = self.get_target_instance(request)
        endpoint = self.match_endpoint_by_label(instance, protocol)
        if not endpoint:
            endpoint = self.match_endpoint_by_target_ip(request, instance, protocol)
        return endpoint

    @staticmethod
    def match_endpoint_by_label(instance, protocol):
        return Endpoint.match_by_instance_label(instance, protocol)

    @staticmethod
    def match_endpoint_by_target_ip(request, instance, protocol):
        # 用来方便测试
        target_ip = request.GET.get('target_ip', '')
        if not target_ip and callable(getattr(instance, 'get_target_ip', None)):
            target_ip = instance.get_target_ip()
        endpoint = EndpointRule.match_endpoint(target_ip, protocol, request)
        return endpoint

    @staticmethod
    def get_target_instance(request):
        asset_id = request.GET.get('asset_id')
        app_id = request.GET.get('app_id')
        session_id = request.GET.get('session_id')
        token_id = request.GET.get('token')
        if token_id:
            from authentication.models import ConnectionToken
            token = ConnectionToken.objects.filter(id=token_id).first()
            if token:
                if token.asset:
                    asset_id = token.asset.id
                elif token.application:
                    app_id = token.application.id
        if asset_id:
            pk, model = asset_id, Asset
        elif app_id:
            pk, model = app_id, Application
        elif session_id:
            pk, model = session_id, Session
        else:
            pk, model = None, None
        if not pk or not model:
            return None
        with tmp_to_root_org():
            instance = get_object_or_404(model, pk=pk)
            return instance


class EndpointViewSet(SmartEndpointViewMixin, JMSBulkModelViewSet):
    filterset_fields = ('name', 'host')
    search_fields = filterset_fields
    serializer_class = serializers.EndpointSerializer
    queryset = Endpoint.objects.all()


class EndpointRuleViewSet(JMSBulkModelViewSet):
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.EndpointRuleSerializer
    queryset = EndpointRule.objects.all()
