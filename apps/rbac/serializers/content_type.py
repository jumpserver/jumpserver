from rest_framework import serializers

from ..models import ContentType

__all__ = ['ContentTypeSerializer']


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ('id', 'app_label', 'model', 'name')
