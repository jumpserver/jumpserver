# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics
from rest_framework.views import Response

from common.drf.serializers import CeleryTaskSerializer
from ..models import AdHoc, AdHocExecution
from ..serializers import (
    AdHocSerializer,
    AdHocExecutionSerializer,
    AdHocDetailSerializer,
)

__all__ = [
    'AdHocViewSet', 'AdHocExecutionViewSet'
]


class AdHocViewSet(viewsets.ModelViewSet):
    queryset = AdHoc.objects.all()
    serializer_class = AdHocSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdHocDetailSerializer
        return super().get_serializer_class()


class AdHocExecutionViewSet(viewsets.ModelViewSet):
    queryset = AdHocExecution.objects.all()
    serializer_class = AdHocExecutionSerializer

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        adhoc_id = self.request.query_params.get('adhoc')

        if task_id:
            task = get_object_or_404(AdHoc, id=task_id)
            adhocs = task.adhoc.all()
            self.queryset = self.queryset.filter(adhoc__in=adhocs)

        if adhoc_id:
            adhoc = get_object_or_404(AdHoc, id=adhoc_id)
            self.queryset = self.queryset.filter(adhoc=adhoc)
        return self.queryset





