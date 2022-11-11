# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from ..models import AdHoc
from ..serializers import (
    AdHocSerializer, AdhocListSerializer,
)

__all__ = [
    'AdHocViewSet'
]


class AdHocViewSet(viewsets.ModelViewSet):
    queryset = AdHoc.objects.all()

    def get_serializer_class(self):
        if self.action != 'list':
            return AdhocListSerializer
        return AdHocSerializer

