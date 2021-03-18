# -*- coding: utf-8 -*-
#
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework_bulk import BulkModelViewSet
from rest_framework.exceptions import MethodNotAllowed
from django.utils.translation import ugettext_lazy as _

from common.mixins import CommonApiMixin, RelationMixin
from orgs.utils import current_org

from ..utils import set_to_root_org

__all__ = [
    'RootOrgViewMixin', 'OrgModelViewSet', 'OrgBulkModelViewSet', 'OrgQuerySetMixin',
    'OrgGenericViewSet', 'OrgRelationMixin'
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


class OrgRelationMixin(RelationMixin):
    def get_queryset(self):
        queryset = super().get_queryset()
        if not current_org.is_root():
            org_id = current_org.org_id()
            queryset = queryset.filter(**{f'{self.from_field}__org_id': org_id})
        return queryset
