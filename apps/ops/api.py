# ~*~ coding: utf-8 ~*~


from rest_framework import viewsets

from .hands import IsSuperUser
from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsSuperUser,)

