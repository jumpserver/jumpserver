# ~*~ coding: utf-8 ~*~


from rest_framework import viewsets

from .hands import IsSuperUser
from .models import Playbook
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Playbook.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsSuperUser,)

