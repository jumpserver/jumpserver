from orgs.mixins.api import OrgBulkModelViewSet
from . import serializers
from .models import Label, LabeledResource

__all__ = ['LabelViewSet']


class LabelViewSet(OrgBulkModelViewSet):
    model = Label
    filterset_fields = ("name", "value")
    search_fields = filterset_fields
    serializer_class = serializers.LabelSerializer


class LabeledResourceViewSet(OrgBulkModelViewSet):
    model = LabeledResource
    serializer_class = serializers.LabeledResourceSerializer
    filterset_fields = ("label__name", "label__value", "res_type", "res_id")
    search_fields = filterset_fields
