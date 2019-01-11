# -*- coding: utf-8 -*-
#

import os
from celery.result import AsyncResult
from rest_framework import generics

from common.permissions import IsValidUser
from common.api import LogTailApi
from ..models import CeleryTask
from ..serializers import CeleryResultSerializer
from ..celery.utils import get_celery_task_log_path


__all__ = ['CeleryTaskLogApi', 'CeleryResultApi']


class CeleryTaskLogApi(LogTailApi):
    permission_classes = (IsValidUser,)
    task = None
    task_id = ''

    def get(self, request, *args, **kwargs):
        self.task_id = str(kwargs.get('pk'))
        self.task = AsyncResult(self.task_id)
        return super().get(request, *args, **kwargs)

    def get_log_path(self):
        new_path = get_celery_task_log_path(self.task_id)
        if new_path and os.path.isfile(new_path):
            return new_path
        try:
            task = CeleryTask.objects.get(id=self.task_id)
        except CeleryTask.DoesNotExist:
            return None
        return task.full_log_path

    def is_file_finish_write(self):
        return self.task.ready()


class CeleryResultApi(generics.RetrieveAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = CeleryResultSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        return AsyncResult(pk)

