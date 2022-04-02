from common.drf.api import JMSBulkModelViewSet
from ..models import Endpoint, EndpointRule
from .. import serializers


__all__ = ['EndpointViewSet', 'EndpointRuleViewSet']


class EndpointViewSet(JMSBulkModelViewSet):
    serializer_class = serializers.EndpointSerializer
    queryset = Endpoint.objects.all()


class EndpointRuleViewSet(JMSBulkModelViewSet):
    serializer_class = serializers.EndpointRuleSerializer
    queryset = EndpointRule.objects.all()
