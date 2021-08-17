from django_filters import rest_framework as filters
from django.db.models import Q
from rest_framework.compat import coreapi, coreschema
from rest_framework.filters import BaseFilterBackend

from common.drf.filters import BaseFilterSet
from users.models.user import User
from users.const import SystemOrOrgRole
from orgs.utils import current_org


class OrgRoleUserFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        org_role = request.query_params.get('org_role')
        if not org_role:
            return queryset

        if org_role == 'admins':
            return queryset & (current_org.admins | User.objects.filter(role=User.ROLE.ADMIN))
        elif org_role == 'auditors':
            return queryset & current_org.auditors
        elif org_role == 'users':
            return queryset & current_org.users
        elif org_role == 'members':
            return queryset & current_org.get_members()

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='org_role', location='query', required=False, type='string',
                schema=coreschema.String(
                    title='Organization role users',
                    description='Organization role users can be {admins|auditors|users|members}'
                )
            )
        ]


class UserFilter(BaseFilterSet):
    system_or_org_role = filters.ChoiceFilter(choices=SystemOrOrgRole.choices, method='filter_system_or_org_role')

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name', 'source', 'system_or_org_role'
        )

    def filter_system_or_org_role(self, queryset, name, value):
        value = value.split('_')
        if len(value) == 1:
            role_type, value = None, value[0]
        else:
            role_type, value = value
        value = value.title()
        system_queries = Q(role=value)
        org_queries = Q(m2m_org_members__role=value, m2m_org_members__org_id=current_org.id)
        if not role_type:
            queries = system_queries | org_queries
        elif role_type == 'system':
            queries = system_queries
        elif role_type == 'org':
            queries = org_queries
        return queryset.filter(queries)
