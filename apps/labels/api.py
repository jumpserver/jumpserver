from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api.generic import JMSModelViewSet
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins.models import OrgModelMixin
from orgs.utils import current_org
from rbac.models import ContentType
from rbac.serializers import ContentTypeSerializer
from . import serializers
from .const import label_resource_types
from .models import Label, LabeledResource

__all__ = ['LabelViewSet', 'ContentTypeViewSet']


class ContentTypeViewSet(JMSModelViewSet):
    serializer_class = ContentTypeSerializer
    http_method_names = ['get', 'head', 'options']
    rbac_perms = {
        'default': 'labels.view_contenttype',
        'resources': 'labels.view_contenttype',
    }
    page_default_limit = None
    can_labeled_content_type = []
    model = ContentType

    def get_queryset(self):
        return label_resource_types

    @action(methods=['GET'], detail=True, serializer_class=serializers.ContentTypeResourceSerializer)
    def resources(self, request, *args, **kwargs):
        self.page_default_limit = 100
        content_type = self.get_object()
        model = content_type.model_class()

        if issubclass(model, OrgModelMixin):
            queryset = model.objects.filter(org_id=current_org.id)
        elif hasattr(model, 'get_queryset'):
            queryset = model.get_queryset()
        else:
            queryset = model.objects.all()

        keyword = request.query_params.get('search')
        if keyword:
            queryset = content_type.filter_queryset(queryset, keyword)
        return self.get_paginated_response_from_queryset(queryset)


class LabelContentTypeResourceViewSet(JMSModelViewSet):
    serializer_class = serializers.ContentTypeResourceSerializer
    rbac_perms = {
        'default': 'labels.view_labeledresource',
        'update': 'labels.change_labeledresource',
    }
    ordering_fields = ('res_type', 'date_created')

    def get_queryset(self):
        label_pk = self.kwargs.get('label')
        res_type = self.kwargs.get('res_type')
        label = get_object_or_404(Label, pk=label_pk)
        content_type = get_object_or_404(ContentType, id=res_type)
        bound = self.request.query_params.get('bound', '1')
        res_ids = LabeledResource.objects \
            .filter(res_type=content_type, label=label) \
            .values_list('res_id', flat=True)
        res_ids = set(res_ids)
        model = content_type.model_class()
        if hasattr(model, 'get_queryset'):
            queryset = model.get_queryset()
        else:
            queryset = model.objects.all()
        if bound == '1':
            queryset = queryset.filter(id__in=list(res_ids))
        else:
            queryset = queryset.exclude(id__in=list(res_ids))
        keyword = self.request.query_params.get('search')
        if keyword:
            queryset = content_type.filter_queryset(queryset, keyword)
        return queryset

    def put(self, request, *args, **kwargs):
        label_pk = self.kwargs.get('label')
        res_type = self.kwargs.get('res_type')
        content_type = get_object_or_404(ContentType, id=res_type)
        label = get_object_or_404(Label, pk=label_pk)
        res_ids = request.data.get('res_ids', [])

        LabeledResource.objects \
            .filter(res_type=content_type, label=label) \
            .exclude(res_id__in=res_ids).delete()
        resources = [
            LabeledResource(res_type=content_type, res_id=res_id, label=label, org_id=current_org.id)
            for res_id in res_ids
        ]
        LabeledResource.objects.bulk_create(resources, ignore_conflicts=True)
        return Response({"total": len(res_ids)})


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
        'keys': 'labels.view_label',
    }

    @action(methods=['GET'], detail=False)
    def keys(self, request, *args, **kwargs):
        queryset = Label.objects.all()
        keyword = request.query_params.get('search')
        if keyword:
            queryset = queryset.filter(name__icontains=keyword)
        keys = queryset.values_list('name', flat=True).distinct()
        return Response(keys)


class LabeledResourceViewSet(OrgBulkModelViewSet):
    model = LabeledResource
    filterset_fields = ("label__name", "label__value", "res_type", "res_id", "label")
    search_fields = []
    serializer_classes = {
        'default': serializers.LabeledResourceSerializer,
    }
    ordering_fields = ('res_type', 'date_created')

    def filter_search(self, queryset):
        keyword = self.request.query_params.get('search')
        if not keyword:
            return queryset
        keyword = keyword.strip().lower()
        matched = []
        offset = 0
        limit = 10000
        while True:
            page = queryset[offset:offset + limit]
            if not page:
                break
            offset += limit
            for instance in page:
                if keyword in str(instance.resource).lower():
                    matched.append(instance.id)
        return queryset.filter(id__in=matched)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.order_by('res_type')
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_search(queryset)
        return queryset
