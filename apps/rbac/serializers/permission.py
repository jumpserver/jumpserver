from rest_framework import serializers
from ..models import Permission


__all__ = ['PermissionSerializer']


class PermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = ['id', 'name', 'content_type', 'codename']
