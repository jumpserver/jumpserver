# -*- coding: utf-8 -*-
from orgs.mixins.api import OrgBulkModelViewSet
from ..models import AdHoc
from ..serializers import (
    AdHocSerializer
)

__all__ = [
    'AdHocViewSet'
]


class AdHocViewSet(OrgBulkModelViewSet):
    serializer_class = AdHocSerializer
    permission_classes = ()
    model = AdHoc

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(creator=self.request.user)
