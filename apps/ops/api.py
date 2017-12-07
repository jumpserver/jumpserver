# ~*~ coding: utf-8 ~*~


from rest_framework import viewsets

from .hands import IsSuperUser
from .models import AdHoc
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    queryset = AdHoc.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsSuperUser,)

