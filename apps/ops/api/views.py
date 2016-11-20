# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response

from serializers import *
from permissions import *

import exc


class HostAliaViewSet(viewsets.GenericViewSet):
    queryset = HostAlia.objects.all()
    serializer_class = HostAliaSerializer
    permission_classes = (AdminUserRequired,)

    def list(self, *args, **kwargs):
        h_alias = self.get_queryset()
        h_serializer = self.get_serializer(h_alias, many=True)
        return Response(h_serializer.data)

    def create(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, *args, **kwargs):
        h_alias = self.get_object()
        serializer = self.get_serializer(h_alias)
        return Response(serializer.data)

    def update(self, *args, **kwargs):
        h_alias = self.get_object()
        serializer = self.get_serializer(h_alias, data=self.request.data)
        serializer.is_valid(raise_exception=False)
        self.perform_create()
        return Response(serializer.data)

    def destroy(self, *args, **kwargs):
        h_alias = self.get_object()
        h_alias.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self):
        pass


class CmdAliaViewSet(viewsets.GenericViewSet):
    queryset = CmdAlia.objects.all()
    serializer_class = CmdAliaSerializer
    permission_classes = (AdminUserRequired,)

    def list(self, *args, **kwargs):
        c_alias = self.get_queryset()
        c_serializer = self.get_serializer(c_alias, many=True)
        return Response(c_serializer.data)

    def create(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, *args, **kwargs):
        c_alias = self.get_object()
        serializer = self.get_serializer(c_alias)
        return Response(serializer.data)

    def update(self, *args, **kwargs):
        c_alias = self.get_object()
        serializer = self.get_serializer(c_alias, data=self.request.data)
        serializer.is_valid(raise_exception=False)
        self.perform_create()
        return Response(serializer.data)

    def destroy(self, *args, **kwargs):
        c_alias = self.get_object()
        c_alias.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self):
        pass


class UserAliaViewSet(viewsets.GenericViewSet):
    queryset = UserAlia.objects.all()
    serializer_class = UserAliaSerializer
    permission_classes = (AdminUserRequired,)

    def list(self, *args, **kwargs):
        u_alias = self.get_queryset()
        u_serializer = self.get_serializer(u_alias, many=True)
        return Response(u_serializer.data)

    def create(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, *args, **kwargs):
        u_alias = self.get_object()
        serializer = self.get_serializer(u_alias)
        return Response(serializer.data)

    def update(self, *args, **kwargs):
        u_alias = self.get_object()
        serializer = self.get_serializer(u_alias, data=self.request.data)
        serializer.is_valid(raise_exception=False)
        self.perform_create()
        return Response(serializer.data)

    def destroy(self, *args, **kwargs):
        u_alias = self.get_object()
        u_alias.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self):
        pass


class RunasAliaViewSet(viewsets.GenericViewSet):
    queryset = RunasAlia.objects.all()
    serializer_class = RunasAliaSerializer
    permission_classes = (AdminUserRequired,)

    def list(self, *args, **kwargs):
        r_alias = self.get_queryset()
        r_serializer = self.get_serializer(r_alias, many=True)
        return Response(r_serializer.data)

    def create(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, *args, **kwargs):
        r_alias = self.get_object()
        serializer = self.get_serializer(r_alias)
        return Response(serializer.data)

    def update(self, *args, **kwargs):
        r_alias = self.get_object()
        serializer = self.get_serializer(r_alias, data=self.request.data)
        serializer.is_valid(raise_exception=False)
        self.perform_create()
        return Response(serializer.data)

    def destroy(self, *args, **kwargs):
        r_alias = self.get_object()
        r_alias.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self):
        pass


class ExtraconfViewSet(viewsets.GenericViewSet):
    queryset = Extra_conf.objects.all()
    serializer_class = ExtraconfSerializer
    permission_classes = (AdminUserRequired,)

    def list(self, *args, **kwargs):
        e_alias = self.get_queryset()
        e_serializer = self.get_serializer(e_alias, many=True)
        return Response(e_serializer.data)

    def create(self, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, *args, **kwargs):
        e_alias = self.get_object()
        serializer = self.get_serializer(e_alias)
        return Response(serializer.data)

    def update(self, *args, **kwargs):
        e_alias = self.get_object()
        serializer = self.get_serializer(e_alias, data=self.request.data)
        serializer.is_valid(raise_exception=False)
        self.perform_create()
        return Response(serializer.data)

    def destroy(self, *args, **kwargs):
        e_alias = self.get_object()
        e_alias.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self):
        pass


class PrivilegeViewSet(viewsets.GenericViewSet):
    queryset = Privilege.objects.all()
    serializer_class = PrivilegeSerializer
    permission_classes = (AdminUserRequired,)

    def list(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def create(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def retrieve(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def update(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def destroy(self, *args, **kwargs):
        privilege = self.get_object()
        privilege.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self):
        pass


class SudoViewSet(viewsets.GenericViewSet):
    queryset = Sudo.objects.all()
    serializer_class = SudoSerializer
    permission_classes = (AdminUserRequired,)

    def list(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def create(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def retrieve(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def update(self, *args, **kwargs):
        raise exc.ServiceNotImplemented

    def destroy(self, *args, **kwargs):
        sudo = self.get_object()
        sudo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self):
        pass


