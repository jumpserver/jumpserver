# -*- coding: utf-8 -*-
#
import uuid
import os

from celery.result import AsyncResult
from django.core.cache import cache
from django.utils.translation import ugettext as _
from rest_framework import generics
from rest_framework.views import Response

from common.permissions import IsOrgAdmin, IsValidUser
from ..models import CeleryTask
from ..serializers import CeleryResultSerializer


__all__ = ['CeleryTaskLogApi', 'CeleryResultApi']


class CeleryTaskLogApi(generics.RetrieveAPIView):
    permission_classes = (IsValidUser,)
    buff_size = 1024 * 10
    end = False
    queryset = CeleryTask.objects.all()

    def get(self, request, *args, **kwargs):
        mark = request.query_params.get("mark") or str(uuid.uuid4())
        task = self.get_object()
        log_path = task.full_log_path

        if not log_path or not os.path.isfile(log_path):
            return Response({"data": _("Waiting ...")}, status=203)

        with open(log_path, 'r') as f:
            offset = cache.get(mark, 0)
            f.seek(offset)
            data = f.read(self.buff_size).replace('\n', '\r\n')
            mark = str(uuid.uuid4())
            cache.set(mark, f.tell(), 5)

            if data == '' and task.is_finished():
                self.end = True
            return Response({"data": data, 'end': self.end, 'mark': mark})


class CeleryResultApi(generics.RetrieveAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = CeleryResultSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        return AsyncResult(pk)

