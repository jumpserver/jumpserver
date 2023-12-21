from rest_framework import viewsets

from .. import serializers
from ..models import ContentType


class ContentTypeViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ContentTypeSerializer
    filterset_fields = ("app_label", "model",)
    search_fields = filterset_fields
    queryset = ContentType.objects.all()
