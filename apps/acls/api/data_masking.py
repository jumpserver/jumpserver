from common.api import JMSBulkModelViewSet

from orgs.utils import tmp_to_root_org
from .common import ACLUserFilterMixin
from ..models import DataMaskingRule
from .. import serializers


__all__ = ['DataMaskingRuleViewSet']


class DataMaskingRuleFilter(ACLUserFilterMixin):
    class Meta:
        model = DataMaskingRule
        fields = ('name', 'action')


class DataMaskingRuleViewSet(JMSBulkModelViewSet):
    queryset = DataMaskingRule.objects.all()
    filterset_class = DataMaskingRuleFilter
    search_fields = ('name',)
    serializer_class = serializers.DataMaskingRuleSerializer

    def filter_queryset(self, queryset):
        with tmp_to_root_org():
            return super().filter_queryset(queryset)
