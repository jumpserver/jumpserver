from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from rbac.utils import get_permission_name


__all__ = ['ContentTypeSerializer', 'PermissionSerializer']


class ContentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContentType
        fields = (
            'id', 'app_label', 'model'
        )
        read_only_fields = ('id',)


class PermissionSerializer(serializers.ModelSerializer):

    name_display = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = (
            'id', 'name', 'name_display', 'content_type', 'codename',
        )
        read_only_fields = ('id',)

    @staticmethod
    def get_name_display(obj):
        return get_permission_name(obj)
