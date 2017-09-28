# ~*~ coding: utf-8 ~*~


from rest_framework import viewsets

from .hands import IsSuperUserOrAppUser
from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """
        对Ansible的task提供的API操作
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsSuperUserOrAppUser,)
