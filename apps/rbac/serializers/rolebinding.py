from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.serializers import CurrentOrgDefault
from ..models import RoleBinding, SystemRoleBinding, OrgRoleBinding

__all__ = [
    'RoleBindingSerializer', 'OrgRoleBindingSerializer',  'SystemRoleBindingSerializer'
]


class RoleBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleBinding
        fields = [
            'id', 'user', 'user_name', 'user_username', 'role', 'role_display',
            'scope', 'org', 'org_name',
        ]
        read_only_fields = ['scope']
        extra_kwargs = {
            'user_name': {'label': _("User Name")},
            'user_username': {'label': _("Username")},
            'role_display': {'label': _('Role display')},
            'org_name': {'label': _("Org name")},
        }


class SystemRoleBindingSerializer(RoleBindingSerializer):
    org = None

    class Meta(RoleBindingSerializer.Meta):
        model = SystemRoleBinding

    def get_field_names(self, *args):
        names = super().get_field_names(*args)
        return list(set(names) - {'org'})


class OrgRoleBindingSerializer(RoleBindingSerializer):
    org = serializers.PrimaryKeyRelatedField(
        default=CurrentOrgDefault(), label=_("Organization"), read_only=True
    )

    class Meta(RoleBindingSerializer.Meta):
        model = OrgRoleBinding
        validators = []

    def validate(self, attrs):
        data = self.initial_data
        many = isinstance(data, list)
        if not many:
            user = attrs.get('user')
            role = attrs.get('role')
            role_bindings = OrgRoleBinding.objects.filter(user=user, role=role)

            if not self.instance and role_bindings.exists():
                raise serializers.ValidationError({'role': _('Has bound this role')})
        return attrs



