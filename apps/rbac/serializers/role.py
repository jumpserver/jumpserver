from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from common.drf.serializers import BulkModelSerializer
from .. import models


__all__ = ['RoleSerializer']


class RoleSerializer(BulkModelSerializer):
    permissions_display = serializers.ListField(
        source='get_permissions_display', read_only=True, label=_('Permission display')
    )
    type_display = serializers.CharField(
        source='get_type_display', read_only=True, label=_('Type display')
    )

    class Meta:
        model = models.Role
        fields = [
            'id', 'display_name', 'name', 'type', 'type_display', 'permissions',
            'permissions_display', 'is_builtin', 'comment', 'created_by', 'date_created',
            'date_updated'
        ]
        extra_kwargs = {
            'created_by': {'read_only': True},
            'date_created': {'read_only': True},
            'date_updated': {'read_only': True},
            'is_builtin': {'read_only': True}
        }
