from django.contrib.contenttypes.models import ContentType
from rest_framework.generics import ListAPIView

from orgs.mixins.api import OrgBulkModelViewSet
from rbac.serializers import ContentTypeSerializer
from . import serializers
from .models import Label, LabeledResource

__all__ = ['LabelViewSet']


class ContentTypeListApi(ListAPIView):
    serializer_class = ContentTypeSerializer

    def get_queryset(self):
        queryset = ContentType.objects.all()
        return queryset


class LabelViewSet(OrgBulkModelViewSet):
    model = Label
    filterset_fields = ("name", "value")
    search_fields = filterset_fields
    serializer_classes = {
        'default': serializers.LabelSerializer,
        'resource_types': ContentTypeSerializer,
    }
    rbac_perms = {
        'resource_types': 'labels.view_label',
    }


class LabeledResourceViewSet(OrgBulkModelViewSet):
    model = LabeledResource
    filterset_fields = ("label__name", "label__value", "res_type", "res_id")
    search_fields = filterset_fields
    serializer_classes = {
        'default': serializers.LabeledResourceSerializer,
    }
