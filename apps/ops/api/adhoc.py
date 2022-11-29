# -*- coding: utf-8 -*-
#

from rest_framework import viewsets

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
