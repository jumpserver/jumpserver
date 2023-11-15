from rest_framework.decorators import action

from common.api.generic import JMSBulkModelViewSet
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins.models import OrgModelMixin
from orgs.utils import current_org
from rbac.models import ContentType
from rbac.serializers import ContentTypeSerializer
from . import serializers
from .models import Label, LabeledResource

__all__ = ['LabelViewSet']


class ContentTypeViewSet(JMSBulkModelViewSet):
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
