from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from rbac.models import Role


class RoleFilter(BaseFilterSet):
    name = filters.CharFilter(method='filter_name')

    class Meta:
        model = Role
        fields = ('name', 'scope', 'builtin')

    @staticmethod
    def filter_name(queryset, name, value):
        builtin_ids = []
        for role in queryset.filter(builtin=True):
            if value in role.display_name:
                builtin_ids.append(role.id)
        if builtin_ids:
            builtin_qs = queryset.model.objects.filter(id__in=builtin_ids)
        else:
            builtin_qs = queryset.model.objects.none()
        queryset = queryset.filter(name__icontains=value)
        return queryset | builtin_qs
