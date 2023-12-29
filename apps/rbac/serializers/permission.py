from django.contrib.auth.models import ContentType
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from ..models import Permission

__all__ = ['PermissionSerializer', 'UserPermsSerializer']


class PermissionContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ['id', 'app_label', 'model']


class PermissionSerializer(serializers.ModelSerializer):
    content_type = PermissionContentTypeSerializer(read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'name', 'content_type', 'codename']


class UserPermsSerializer(serializers.Serializer):
    perms = serializers.ListField(label=_('Perms'), read_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
