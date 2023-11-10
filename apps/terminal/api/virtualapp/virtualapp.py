from common.api import JMSBulkModelViewSet
from terminal import serializers
from terminal.models import VirtualApp

__all__ = ['VirtualAppViewSet', ]


class VirtualAppViewSet(JMSBulkModelViewSet):
    queryset = VirtualApp.objects.all()
    serializer_class = serializers.VirtualAppSerializer
    filterset_fields = ['name', 'is_active']
    search_fields = ['name', ]
