# ~*~ coding: utf-8 ~*~


from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics
from rest_framework.views import Response

from .hands import IsSuperUser
from .models import Task, AdHoc, AdHocRunHistory
from .serializers import TaskSerializer, AdHocSerializer, AdHocRunHistorySerializer
from .tasks import run_ansible_task


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsSuperUser,)


class TaskRun(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskViewSet
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        run_ansible_task.delay(str(task.id))
        return Response({"msg": "start"})


class AdHocViewSet(viewsets.ModelViewSet):
    queryset = AdHoc.objects.all()
    serializer_class = AdHocSerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            self.queryset = self.queryset.filter(task=task)
        return self.queryset


class AdHocRunHistorySet(viewsets.ModelViewSet):
    queryset = AdHocRunHistory.objects.all()
    serializer_class = AdHocRunHistorySerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        adhoc_id = self.request.query_params.get('adhoc')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            adhocs = task.adhoc.all()
            self.queryset = self.queryset.filter(adhoc__in=adhocs)

        if adhoc_id:
            adhoc = get_object_or_404(AdHoc, id=adhoc_id)
            self.queryset = self.queryset.filter(adhoc=adhoc)
        return self.queryset
