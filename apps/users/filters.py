from rest_framework.compat import coreapi, coreschema
from rest_framework import filters

from users.models.user import User
from orgs.utils import current_org


class OrgRoleUserFilterBackend(filters.BaseFilterBackend):
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
