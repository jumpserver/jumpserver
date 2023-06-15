from django.utils.translation import gettext as _
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from common.utils import is_uuid
from rbac.models import Role
from users.models.user import User


class UserFilter(BaseFilterSet):
    system_roles = filters.CharFilter(method='filter_system_roles')
    org_roles = filters.CharFilter(method='filter_org_roles')
    groups = filters.CharFilter(field_name="groups__name", lookup_expr='exact')
    group_id = filters.CharFilter(field_name="groups__id", lookup_expr='exact')
    exclude_group_id = filters.CharFilter(
        field_name="groups__id", lookup_expr='exact', exclude=True
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name',
            'groups', 'group_id', 'exclude_group_id',
            'source', 'org_roles', 'system_roles', 'is_active',
        )

    @staticmethod
    def get_role(value):
        from rbac.builtin import BuiltinRole
        roles = BuiltinRole.get_roles()
        for role in roles.values():
            if _(role.name) == value:
                return role

        if is_uuid(value):
            return Role.objects.filter(id=value).first()
        else:
            return Role.objects.filter(name=value).first()

    def filter_system_roles(self, queryset, name, value):
        role = self.get_role(value)
        if not role:
            return queryset.none()
        queryset = queryset.prefetch_related('role_bindings') \
            .filter(role_bindings__role_id=role.id) \
            .filter(role_bindings__role__scope='system') \
            .distinct()
        return queryset

    def filter_org_roles(self, queryset, name, value):
        role = self.get_role(value)
        if not role:
            return queryset.none()
        queryset = queryset.prefetch_related('role_bindings') \
            .filter(role_bindings__role_id=role.id) \
            .filter(role_bindings__role__scope='org') \
            .distinct()
        return queryset
