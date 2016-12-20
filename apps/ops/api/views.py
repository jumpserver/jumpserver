# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import viewsets

from serializers import *
from permissions import *

__all__ = ["HostAliaViewSet",
           "CmdAliaViewSet",
           "UserAliaViewSet",
           "RunasAliaViewSet",
           "ExtraconfViewSet",
           "PrivilegeViewSet",
           "SudoViewSet",
           "CronTableViewSet",
           "TaskViewSet",
           "SubTaskViewSet",
           ]


class HostAliaViewSet(viewsets.ModelViewSet):
    queryset = HostAlia.objects.all()
    serializer_class = HostAliaSerializer
    permission_classes = (AdminUserRequired,)


class CmdAliaViewSet(viewsets.ModelViewSet):
    queryset = CmdAlia.objects.all()
    serializer_class = CmdAliaSerializer
    permission_classes = (AdminUserRequired,)


class UserAliaViewSet(viewsets.ModelViewSet):
    queryset = UserAlia.objects.all()
    serializer_class = UserAliaSerializer
    permission_classes = (AdminUserRequired,)


class RunasAliaViewSet(viewsets.ModelViewSet):
    queryset = RunasAlia.objects.all()
    serializer_class = RunasAliaSerializer
    permission_classes = (AdminUserRequired,)


class ExtraconfViewSet(viewsets.ModelViewSet):
    queryset = Extra_conf.objects.all()
    serializer_class = ExtraconfSerializer
    permission_classes = (AdminUserRequired,)


class PrivilegeViewSet(viewsets.ModelViewSet):
    queryset = Privilege.objects.all()
    serializer_class = PrivilegeSerializer
    permission_classes = (AdminUserRequired,)


class SudoViewSet(viewsets.ModelViewSet):
    queryset = Sudo.objects.all()
    serializer_class = SudoSerializer
    permission_classes = (AdminUserRequired,)


class CronTableViewSet(viewsets.ModelViewSet):
    queryset = CronTable.objects.all()
    serializer_class = CronTableSerializer
    permission_classes = (AdminUserRequired,)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (AdminUserRequired,)

class SubTaskViewSet(viewsets.ModelViewSet):
    queryset = SubTask.objects.all()
    serializer_class = SubTaskSerializer
    permission_classes = (AdminUserRequired,)



