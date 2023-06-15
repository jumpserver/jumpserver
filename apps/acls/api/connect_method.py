from django_filters import rest_framework as drf_filters

from common.api import JMSBulkModelViewSet
from orgs.utils import tmp_to_root_org
from .common import ACLUserFilterMixin
from .. import serializers
from ..models import ConnectMethodACL

__all__ = ['ConnectMethodACLViewSet']


class ConnectMethodFilter(ACLUserFilterMixin):
    methods = drf_filters.CharFilter(field_name="methods__contains", lookup_expr='exact')

    class Meta:
        model = ConnectMethodACL
        fields = ['name', ]


class ConnectMethodACLViewSet(JMSBulkModelViewSet):
    queryset = ConnectMethodACL.objects.all()
    filterset_class = ConnectMethodFilter
    search_fields = ('name',)
    serializer_class = serializers.ConnectMethodACLSerializer

    def filter_queryset(self, queryset):
        with tmp_to_root_org():
            return super().filter_queryset(queryset)

