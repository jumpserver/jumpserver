# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework_bulk import BulkModelViewSet
from common.mixins import CommonApiMixin, RelationMixin
from orgs.utils import current_org

from ..utils import set_to_root_org
from ..models import Organization

__all__ = [
    'RootOrgViewMixin', 'OrgMembershipModelViewSetMixin', 'OrgModelViewSet',
    'OrgBulkModelViewSet', 'OrgQuerySetMixin', 'OrgGenericViewSet', 'OrgRelationMixin'
]


class RootOrgViewMixin:
    def dispatch(self, request, *args, **kwargs):
        set_to_root_org()
        return super().dispatch(request, *args, **kwargs)


class OrgQuerySetMixin:
    def get_queryset(self):
        if hasattr(self, 'model'):
            queryset = self.model.objects.all()
        else:
            assert self.queryset is None, (
                    "'%s' should not include a `queryset` attribute"
                    % self.__class__.__name__
            )
            queryset = super().get_queryset()

        if hasattr(self, 'swagger_fake_view'):
            return queryset[:1]
        if hasattr(self, 'action') and self.action == 'list':
            serializer_class = self.get_serializer_class()
            if serializer_class and hasattr(serializer_class, 'setup_eager_loading'):
                queryset = serializer_class.setup_eager_loading(queryset)
        return queryset


class OrgModelViewSet(CommonApiMixin, OrgQuerySetMixin, ModelViewSet):
    pass


class OrgGenericViewSet(CommonApiMixin, OrgQuerySetMixin, GenericViewSet):
    pass


class OrgBulkModelViewSet(CommonApiMixin, OrgQuerySetMixin, BulkModelViewSet):
    def allow_bulk_destroy(self, qs, filtered):
        qs_count = qs.count()
        filtered_count = filtered.count()
        if filtered_count == 1:
            return True
        if qs_count > filtered_count:
            return True
        if self.request.query_params.get('spm', ''):
            return True
        return False


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


class OrgRelationMixin(RelationMixin):
    def get_queryset(self):
        queryset = super().get_queryset()
        org_id = current_org.org_id()
        if org_id is not None:
            queryset = queryset.filter(**{f'{self.from_field}__org_id': org_id})
        return queryset
