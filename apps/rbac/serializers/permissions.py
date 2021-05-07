from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from django.contrib.auth.models import Permission


__all__ = ['PermissionSerializer']


class PermissionSerializer(serializers.ModelSerializer):
    content_type_display = serializers.CharField(
        source='content_type.app_labeled_name', label=_('Content type display')
    )

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type', 'content_type_display']
