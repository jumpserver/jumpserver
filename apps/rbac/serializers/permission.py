from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers


__all__ = ['ContentTypeSerializer', 'PermissionSerializer']


class ContentTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = ContentType
        fields = (
            'id', 'app_label', 'model'
        )
        read_only_fields = ('id',)


class PermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = (
            'id', 'name', 'content_type', 'codename',
        )
        read_only_fields = ('id',)

