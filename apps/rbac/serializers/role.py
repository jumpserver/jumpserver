from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from users.models import User
from ..models import Role

__all__ = ['RoleSerializer', 'RoleUserSerializer']


class RoleSerializer(serializers.ModelSerializer):
    scope = LabeledChoiceField(choices=Role.Scope.choices, label=_("Scope"))

    class Meta:
        model = Role
        fields_mini = ['id', 'name', 'display_name', 'scope']
        read_only_fields = [
            'users_amount', 'builtin',
            'date_created', 'date_updated',
            'created_by', 'updated_by',
        ]
        fields = fields_mini + read_only_fields + [
            'comment', 'permissions'
        ]
        extra_kwargs = {
            'permissions': {'write_only': True},
            'users_amount': {'label': _('Users amount')},
            'display_name': {'label': _('Display name')}
        }


class RoleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username']
