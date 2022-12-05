# -*- coding: utf-8 -*-
#

from rest_framework_bulk import BulkModelViewSet

from common.mixins import CommonApiMixin
from ..models import AdHoc
from ..serializers import (
    AdHocSerializer
)

__all__ = [
    'AdHocViewSet'
]


class AdHocViewSet(CommonApiMixin, BulkModelViewSet):
    serializer_class = AdHocSerializer
    permission_classes = ()

    def get_queryset(self):
        return AdHoc.objects.filter(creator=self.request.user)
