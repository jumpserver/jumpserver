# -*- coding: utf-8 -*-
from .base import SelfBulkModelViewSet
from ..models import AdHoc
from ..serializers import (
    AdHocSerializer
)

__all__ = [
    'AdHocViewSet'
]


class AdHocViewSet(SelfBulkModelViewSet):
    serializer_class = AdHocSerializer
    permission_classes = ()
    model = AdHoc
