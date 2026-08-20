from django_filters import rest_framework as drf_filters
from django.utils.translation import gettext_lazy as _

from common.api import JMSBulkModelViewSet
from orgs.utils import tmp_to_root_org
from .common import ACLUserFilterMixin
from .. import serializers
from ..models import ConnectMethodACL

__all__ = ['ConnectMethodACLViewSet']


class ConnectMethodFilter(ACLUserFilterMixin):
    methods = drf_filters.CharFilter(
        method="filter_methods",
        label=_("Connect methods"),
    )

    class Meta:
        model = ConnectMethodACL
        fields = ['id', 'name', 'users', 'methods', 'action']
        fields_operator = {
            'methods': ('icontains_all',),
        }

    @staticmethod
    def filter_methods(queryset, name, value):
        methods = [method.strip() for method in value.split(',') if method.strip()]
        if not methods:
            return queryset
        return queryset.filter(connect_methods__contains=methods)


class ConnectMethodACLViewSet(JMSBulkModelViewSet):
    queryset = ConnectMethodACL.objects.all()
    filterset_class = ConnectMethodFilter
    search_fields = ('name',)
    serializer_class = serializers.ConnectMethodACLSerializer

    def filter_queryset(self, queryset):
        with tmp_to_root_org():
            return super().filter_queryset(queryset)
