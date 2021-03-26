from rest_framework import serializers
from django.contrib.auth.models import Permission


__all__ = ['RolePermissionSerializer']


class RolePermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = ['id', 'name', 'content_type', 'codename']
