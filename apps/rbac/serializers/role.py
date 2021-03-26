from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from common.drf.serializers import BulkModelSerializer
from ..models import Role, RoleTypeChoices


__all__ = ['RoleSerializer']


class RoleSerializer(BulkModelSerializer):
    permissions_display = serializers.ListField(
        source='get_permissions_display', read_only=True, label=_('Permission display')
    )
    type_display = serializers.CharField(
        source='get_type_display', read_only=True, label=_('Type display')
    )

    class Meta:
        model = Role
        fields = [
            'id', 'display_name', 'name', 'type', 'type_display', 'permissions',
            'permissions_display', 'is_builtin', 'comment', 'created_by', 'date_created',
            'date_updated'
        ]
        extra_kwargs = {
            'created_by': {'read_only': True},
            'date_created': {'read_only': True},
            'date_updated': {'read_only': True},
            'is_builtin': {'read_only': True},
            'type': {'required': True},
        }

    def validate_permissions(self, permissions):
        if self.instance:
            role_type = self.instance.type
        else:
            role_type = self.initial_data.get('type')

        if role_type not in RoleTypeChoices.names:
            raise serializers.ValidationError('The `type` is invalid: {}'.format(role_type))

        permissions_ids = [permission.id for permission in permissions]
        allowed_permissions_ids = RoleTypeChoices\
            .get_permissions(role_type)\
            .values_list('id', flat=True)
        disallowed_permissions_ids = set(permissions_ids) - set(allowed_permissions_ids)
        if disallowed_permissions_ids:
            error = _('These permissions are not allowed: {}'.format(disallowed_permissions_ids))
            raise serializers.ValidationError(error)
        return permissions
