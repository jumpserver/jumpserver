# -*- coding: utf-8 -*-
#
from collections import OrderedDict
import copy
from rest_framework import viewsets, serializers
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Terminal, TerminalStatus, TerminalSession, TerminalTask
from .serializers import TerminalSerializer, TerminalStatusSerializer, \
    TerminalSessionSerializer, TerminalTaskSerializer
from .hands import IsSuperUserOrAppUser, IsAppUser, ProxyLog, \
    IsSuperUserOrAppUserOrUserReadonly
from common.utils import get_object_or_none


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = TerminalSerializer
    permission_classes = (IsSuperUserOrAppUserOrUserReadonly,)

    def create(self, request, *args, **kwargs):
        name = request.data.get('name')
        remote_ip = request.META.get('REMOTE_ADDR')
        x_real_ip = request.META.get('X-Real-IP')
        remote_addr = x_real_ip or remote_ip

        terminal = get_object_or_none(Terminal, name=name)
        if terminal:
            msg = 'Terminal name %s already used' % name
            return Response({'msg': msg}, status=409)

        serializer = self.serializer_class(data={
            'name': name, 'remote_addr': remote_addr
        })

        if serializer.is_valid():
            terminal = serializer.save()
            app_user, access_key = terminal.create_app_user()
            data = OrderedDict()
            data['terminal'] = copy.deepcopy(serializer.data)
            data['user'] = app_user.to_json()
            data['access_key'] = {'id': access_key.id,
                                  'secret': access_key.secret}
            return Response(data, status=201)
        else:
            data = serializer.errors
            return Response(data, status=400)

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = (AllowAny,)
        return super().get_permissions()


class TerminalStatusViewSet(viewsets.ModelViewSet):
    queryset = TerminalStatus.objects.all()
    serializer_class = TerminalStatusSerializer
    permission_classes = (IsSuperUserOrAppUser,)
    session_serializer_class = TerminalSessionSerializer

    def create(self, request, *args, **kwargs):
        sessions_active = []
        for session_data in request.data.get("sessions", []):
            session_data["terminal"] = self.request.user.terminal.id
            _id = session_data["id"]
            session = get_object_or_none(TerminalSession, id=_id)
            if session:
                serializer = TerminalSessionSerializer(data=session_data, instance=session)
            else:
                serializer = TerminalSessionSerializer(data=session_data)

            if serializer.is_valid():
                serializer.save()

            if session_data["is_finished"]:
                sessions_active.append(session_data["id"])

        sessions_in_db_active = TerminalSession.objects.filter(
            is_finished=False, terminal=self.request.user.terminal.id
        )

        for session in sessions_in_db_active:
            if session.id not in sessions_active:
                session.is_finished = True
                session.date_end = timezone.now()
                session.save()

        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        terminal_id = self.kwargs.get("terminal", None)
        if terminal_id:
            terminal = get_object_or_404(Terminal, id=terminal_id)
            self.queryset = terminal.terminalstatus_set.all()
        return self.queryset

    def perform_create(self, serializer):
        serializer.validated_data["terminal"] = self.request.user.terminal
        return super().perform_create(serializer)

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = (IsAppUser,)
        return super().get_permissions()


class TerminalSessionViewSet(viewsets.ModelViewSet):
    queryset = TerminalSession.objects.all()
    serializers_class = TerminalSessionSerializer
    permission_classes = (IsSuperUserOrAppUser,)

    def get_queryset(self):
        terminal_id = self.kwargs.get("terminal", None)
        if terminal_id:
            terminal = get_object_or_404(Terminal, id=terminal_id)
            self.queryset = terminal.terminalstatus_set.all()
        return self.queryset


class TerminalTaskViewSet(viewsets.ModelViewSet):
    queryset = TerminalTask.objects.all()
    serializer_class = TerminalTaskSerializer
    permission_classes = (IsSuperUserOrAppUser,)

    def get_queryset(self):
        terminal_id = self.kwargs.get("terminal", None)
        if terminal_id:
            terminal = get_object_or_404(Terminal, id=terminal_id)
            self.queryset = terminal.terminalstatus_set.all()

        if hasattr(self.request.user, "terminal"):
            terminal = self.request.user.terminal
            self.queryset = terminal.terminalstatus_set.all()
        return self.queryset
