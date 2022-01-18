from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from users.models import User
from ..models import Role

__all__ = ['RoleSerializer', 'RoleUserSerializer']


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields_mini = ['id', 'name', 'display_name', 'scope']
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
            'display_name': {'label': _('Name display')}
        }


class RoleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username']
