# -*- coding: utf-8 -*-
#
from django.db.models import QuerySet
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework_bulk import BulkModelViewSet

from common.api import CommonApiMixin, RelationMixin
from orgs.utils import current_org
from ..utils import set_to_root_org

__all__ = [
    'RootOrgViewMixin', 'OrgModelViewSet', 'OrgBulkModelViewSet', 'OrgQuerySetMixin',
    'OrgGenericViewSet', 'OrgRelationMixin', 'OrgReadonlyModelViewSet'
]


class RootOrgViewMixin:
    def dispatch(self, request, *args, **kwargs):
        set_to_root_org()
        return super().dispatch(request, *args, **kwargs)


class OrgQuerySetMixin:
    queryset: QuerySet
    get_serializer_class: callable
    action: str

    def get_queryset(self):
        if hasattr(self, 'model'):
            queryset = self.model.objects.all()
        else:
            assert self.queryset is None, (
                    "'%s' should not include a `queryset` attribute"
                    % self.__class__.__name__
            )
            queryset = super().get_queryset()
        return queryset


class OrgViewSetMixin(OrgQuerySetMixin):
    pass


class OrgModelViewSet(CommonApiMixin, OrgViewSetMixin, ModelViewSet):
    pass


class OrgGenericViewSet(CommonApiMixin, OrgViewSetMixin, GenericViewSet):
    pass


class OrgBulkModelViewSet(CommonApiMixin, OrgViewSetMixin, BulkModelViewSet):
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


class OrgReadonlyModelViewSet(OrgModelViewSet):
    http_method_names = ['get', 'head', 'options']


class OrgRelationMixin(RelationMixin):
    def get_queryset(self):
        queryset = super().get_queryset()
        if not current_org.is_root():
            org_id = current_org.org_id()
            queryset = queryset.filter(**{f'{self.from_field}__org_id': org_id})
        return queryset
