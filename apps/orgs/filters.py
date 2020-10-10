from django_filters.rest_framework import filterset
from django_filters.rest_framework import filters

from .models import OrganizationMember


class UUIDInFilter(filters.BaseInFilter, filters.UUIDFilter):
    pass


class OrgMemberRelationFilterSet(filterset.FilterSet):
    id = UUIDInFilter(field_name='id', lookup_expr='in')

    class Meta:
        model = OrganizationMember
        fields = ('org_id', 'user_id', 'org', 'user', 'role', 'id')
