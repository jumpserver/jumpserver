from rest_framework import viewsets

from common.api import JMSBulkModelViewSet
from terminal import serializers
from terminal.models import VirtualAppPublication, VirtualApp

__all__ = ['VirtualAppViewSet', 'VirtualAppPublicationViewSet']


class VirtualAppViewSet(JMSBulkModelViewSet):
    queryset = VirtualApp.objects.all()
    serializer_class = serializers.VirtualAppSerializer
    filterset_fields = ['name', 'image_name', 'is_active']
    search_fields = ['name', ]


class VirtualAppPublicationViewSet(viewsets.ModelViewSet):
    queryset = VirtualAppPublication.objects.all()
    serializer_class = serializers.VirtualAppPublicationSerializer
    filterset_fields = ['app__name', 'vhost__name', 'status']
    search_fields = ['app__name', 'vhost__name', ]
