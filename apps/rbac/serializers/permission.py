from django.contrib.auth.models import ContentType
from rest_framework import serializers

from ..models import Permission

__all__ = ['PermissionSerializer']


class PermissionContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']


class PermissionSerializer(serializers.ModelSerializer):
    content_type = PermissionContentTypeSerializer(read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'name', 'content_type', 'codename']
