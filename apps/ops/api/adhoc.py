# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from ..models import AdHoc
from ..serializers import (
    AdHocSerializer
)

__all__ = [
    'AdHocViewSet'
]


class AdHocViewSet(viewsets.ModelViewSet):
    queryset = AdHoc.objects.all()
    serializer_class = AdHocSerializer
