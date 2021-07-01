from rest_framework import serializers

from ..models import Role, RoleBinding

__all__ = ['RoleSerializer', 'RoleBindingSerializer']


class RoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'type', 'permissions', 'builtin', 'comment',
            'date_created', 'date_updated', 'created_by', 'updated_by'
        ]
        read_only_fields = [
            'builtin', 'date_created', 'date_updated', 'created_by', 'updated_by'
        ]


class RoleBindingSerializer(serializers.ModelSerializer):

    class Meta:
        model = RoleBinding
        fields = ['id', 'type', 'user', 'role', 'org']
        read_only_fields = ['type']
