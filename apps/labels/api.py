from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api.generic import JMSModelViewSet
from common.utils import is_true
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins.models import OrgModelMixin
from orgs.utils import current_org
from rbac.models import ContentType
from rbac.serializers import ContentTypeSerializer
from . import serializers
from .models import Label, LabeledResource

__all__ = ['LabelViewSet']


class ContentTypeViewSet(JMSModelViewSet):
    serializer_class = ContentTypeSerializer
    http_method_names = ['get', 'head', 'options']
    rbac_perms = {
        'default': 'labels.view_contenttype',
        'resources': 'labels.view_contenttype',
    }
    exclude_apps = (
        'admin',
        'applications',
        'auth',
        'authentication',
        'captcha',
        'contenttypes',
        'django_cas_ng',
        'django_celery_beat',
        'jms_oidc_rp',
        'notifications',
        'passkeys',
        'rbac',
        'sessions',
        'settings',
        'xpack',
        'labels',
    )
    page_default_limit = None

    def get_queryset(self):
        queryset = ContentType.objects.all().exclude(app_label__in=self.exclude_apps)
        return queryset

    @action(methods=['GET'], detail=True, serializer_class=serializers.ContentTypeResourceSerializer)
    def resources(self, request, *args, **kwargs):
        self.page_default_limit = 100
        content_type = self.get_object()
        model = content_type.model_class()

        if issubclass(model, OrgModelMixin):
            queryset = model.objects.filter(org_id=current_org.id)
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

    def get_queryset(self):
        label_pk = self.kwargs.get('label')
        res_type = self.kwargs.get('res_type')
        label = get_object_or_404(Label, pk=label_pk)
        content_type = get_object_or_404(ContentType, id=res_type)
        bound = self.request.query_params.get('bound', '1')
        res_ids = LabeledResource.objects.filter(res_type=content_type, label=label) \
            .values_list('res_id', flat=True)
        res_ids = set(res_ids)
        model = content_type.model_class()
        if is_true(bound):
            queryset = model.objects.filter(id__in=list(res_ids))
        else:
            queryset = model.objects.exclude(id__in=list(res_ids))
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
        print("res_ids", res_ids)

        LabeledResource.objects.filter(res_type=content_type, label=label).exclude(res_id__in=res_ids).delete()
        resources = []
        for res_id in res_ids:
            resources.append(LabeledResource(res_type=content_type, res_id=res_id, label=label, org_id=current_org.id))
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
    }


class LabeledResourceViewSet(OrgBulkModelViewSet):
    model = LabeledResource
    filterset_fields = ("label__name", "label__value", "res_type", "res_id", "label")
    search_fields = filterset_fields
    serializer_classes = {
        'default': serializers.LabeledResourceSerializer,
    }
    ordering_fields = ('res_type', 'date_created')
