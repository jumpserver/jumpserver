# ~*~ coding: utf-8 ~*~

from rest_framework_bulk import BulkModelViewSet
from rest_framework.views import APIView, Response
from rest_framework.generics import RetrieveAPIView

from django.views.generic.detail import SingleObjectMixin

from common.utils import get_logger
from ..hands import IsSuperUser, IsSuperUserOrAppUser
from ..models import Domain, Gateway
from ..utils import test_gateway_connectability
from .. import serializers


logger = get_logger(__file__)
__all__ = ['DomainViewSet', 'GatewayViewSet', "GatewayTestConnectionApi"]


class DomainViewSet(BulkModelViewSet):
    queryset = Domain.objects.all()
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.DomainSerializer

    def get_serializer_class(self):
        if self.request.query_params.get('gateway'):
            return serializers.DomainWithGatewaySerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.request.query_params.get('gateway'):
            self.permission_classes = (IsSuperUserOrAppUser,)
        return super().get_permissions()


class GatewayViewSet(BulkModelViewSet):
    filter_fields = ("domain",)
    search_fields = filter_fields
    queryset = Gateway.objects.all()
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.GatewaySerializer


class GatewayTestConnectionApi(SingleObjectMixin, APIView):
    permission_classes = (IsSuperUser,)
    model = Gateway
    object = None

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(Gateway.objects.all())
        ok, e = test_gateway_connectability(self.object)
        if ok:
            return Response("ok")
        else:
            return Response({"failed": e}, status=404)
