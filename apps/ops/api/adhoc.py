# -*- coding: utf-8 -*-
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission
from ..models import AdHoc
from ..serializers import (
    AdHocSerializer
)

__all__ = [
    'AdHocViewSet'
]


class AdHocViewSet(OrgBulkModelViewSet):
    serializer_class = AdHocSerializer
    permission_classes = (RBACPermission,)
    search_fields = ('name', 'comment')
    model = AdHoc

    def allow_bulk_destroy(self, qs, filtered):
        return True

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(creator=self.request.user)
