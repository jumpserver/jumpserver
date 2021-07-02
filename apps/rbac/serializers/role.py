from rest_framework import serializers

from ..models import Role, RoleBinding
from ..const import ScopeChoices

__all__ = ['RoleSerializer', 'RoleBindingSerializer']


class RoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'scope', 'permissions', 'builtin', 'comment',
            'date_created', 'date_updated', 'created_by', 'updated_by'
        ]
        read_only_fields = [
            'builtin', 'date_created', 'date_updated', 'created_by', 'updated_by'
        ]


class RoleBindingSerializer(serializers.ModelSerializer):

    class Meta:
        model = RoleBinding
        fields = ['id', 'scope', 'user', 'role', 'org']
        read_only_fields = ['scope']
