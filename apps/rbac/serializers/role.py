from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from ..models import Role, RoleBinding

__all__ = ['RoleSerializer', 'RoleBindingSerializer']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields_mini = ['id', 'name', 'name_display', 'scope']
        read_only_fields = [
            'users_amount', 'builtin', 'date_created',
            'date_updated', 'created_by', 'updated_by'
        ]
        fields = fields_mini + read_only_fields + [
            'comment', 'permissions'
        ]
        extra_kwargs = {
            'permissions': {'write_only': True},
            'users_amount': {'label': _('Users amount')},
            'name_display': {'label': _('Name display')}
        }


class RoleBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleBinding
        fields = ['id', 'scope', 'user', 'role', 'org']
        read_only_fields = ['scope']
