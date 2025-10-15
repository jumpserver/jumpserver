from orgs.mixins.api import OrgBulkModelViewSet

from .common import ACLUserFilterMixin
from ..models import DataMaskingRule
from .. import serializers


__all__ = ['DataMaskingRuleViewSet']


class DataMaskingRuleFilter(ACLUserFilterMixin):
    class Meta:
        model = DataMaskingRule
        fields = ('name', 'action')


class DataMaskingRuleViewSet(OrgBulkModelViewSet):
    model = DataMaskingRule
    filterset_class = DataMaskingRuleFilter
    search_fields = ('name',)
    serializer_class = serializers.DataMaskingRuleSerializer
