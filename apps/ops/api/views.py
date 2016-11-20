# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import viewsets, mixins

from serializers import *
from permissions import *


class HostAliaViewSet(mixins.CreateModelMixin,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    queryset = HostAlia.objects.all()
    serializer_class = HostAliaSerializer
    permission_classes = (AdminUserRequired,)


class CmdAliaViewSet(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    queryset = CmdAlia.objects.all()
    serializer_class = CmdAliaSerializer
    permission_classes = (AdminUserRequired,)


class UserAliaViewSet(mixins.CreateModelMixin,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    queryset = UserAlia.objects.all()
    serializer_class = UserAliaSerializer
    permission_classes = (AdminUserRequired,)


class RunasAliaViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    queryset = RunasAlia.objects.all()
    serializer_class = RunasAliaSerializer
    permission_classes = (AdminUserRequired,)


class ExtraconfViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    queryset = Extra_conf.objects.all()
    serializer_class = ExtraconfSerializer
    permission_classes = (AdminUserRequired,)


class PrivilegeViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    queryset = Privilege.objects.all()
    serializer_class = PrivilegeSerializer
    permission_classes = (AdminUserRequired,)


class SudoViewSet(mixins.CreateModelMixin,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  viewsets.GenericViewSet):
    queryset = Sudo.objects.all()
    serializer_class = SudoSerializer
    permission_classes = (AdminUserRequired,)



