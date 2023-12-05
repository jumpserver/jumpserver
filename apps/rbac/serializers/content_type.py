from rest_framework import serializers

from ..models import ContentType

__all__ = ['ContentTypeSerializer']


class ContentTypeSerializer(serializers.ModelSerializer):
    app_display = serializers.CharField()

    class Meta:
        model = ContentType
        fields = ('id', 'app_label', 'app_display', 'model', 'name')
