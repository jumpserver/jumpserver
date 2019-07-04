# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework_bulk import BulkModelViewSet
from common.mixins import IDInCacheFilterMixin

from ..utils import set_to_root_org
from ..models import Organization

__all__ = [
    'RootOrgViewMixin', 'OrgMembershipModelViewSetMixin', 'OrgModelViewSet',
    'OrgBulkModelViewSet',
]


class RootOrgViewMixin:
    def dispatch(self, request, *args, **kwargs):
        set_to_root_org()
        return super().dispatch(request, *args, **kwargs)


class OrgModelViewSet(IDInCacheFilterMixin, ModelViewSet):
    def get_queryset(self):
        return super().get_queryset().all()


class OrgBulkModelViewSet(IDInCacheFilterMixin, BulkModelViewSet):
    def get_queryset(self):
        queryset = super().get_queryset().all()
        if hasattr(self, 'action') and self.action == 'list' and \
            hasattr(self, 'serializer_class') and \
                hasattr(self.serializer_class, 'setup_eager_loading'):
            queryset = self.serializer_class.setup_eager_loading(queryset)
        return queryset


class OrgMembershipModelViewSetMixin:
    org = None
    membership_class = None
    lookup_field = 'user'
    lookup_url_kwarg = 'user_id'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def dispatch(self, request, *args, **kwargs):
        self.org = get_object_or_404(Organization, pk=kwargs.get('org_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['org'] = self.org
        return context

    def get_queryset(self):
        queryset = self.membership_class.objects.filter(organization=self.org)
        return queryset
