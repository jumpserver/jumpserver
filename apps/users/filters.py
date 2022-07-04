from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from users.models.user import User
from rbac.models import Role


class UserFilter(BaseFilterSet):
    system_roles = filters.ModelChoiceFilter(
        queryset=Role.objects.filter(scope='system'), method='filter_system_roles'
    )
    org_roles = filters.ModelChoiceFilter(
        queryset=Role.objects.filter(scope='org'), method='filter_org_roles'
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'source',
            'org_roles', 'system_roles', 'is_active',
        )

    @staticmethod
    def filter_system_roles(queryset, name, value):
        queryset = queryset.prefetch_related('role_bindings')\
            .filter(role_bindings__role_id=value.id)\
            .distinct()
        return queryset

    @staticmethod
    def filter_org_roles(queryset, name, value):
        queryset = queryset.prefetch_related('role_bindings') \
            .filter(role_bindings__role_id=value.id) \
            .distinct()
        return queryset


