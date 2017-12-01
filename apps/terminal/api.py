# -*- coding: utf-8 -*-
#
import base64
from collections import OrderedDict
import copy
import logging
import tarfile

import os
from rest_framework import viewsets, serializers
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings

from common.utils import get_object_or_none
from .models import Terminal, Status, Session, Task
from .serializers import TerminalSerializer, TerminalStatusSerializer, \
    TerminalSessionSerializer, TerminalTaskSerializer
from .hands import IsSuperUserOrAppUser, IsAppUser, ProxyLog, \
    IsSuperUserOrAppUserOrUserReadonly
from .backends import get_command_store, get_replay_store, SessionCommandSerializer

logger = logging.getLogger(__file__)


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
    queryset = Status.objects.all()
    serializer_class = TerminalStatusSerializer
    permission_classes = (IsSuperUserOrAppUser,)
    session_serializer_class = TerminalSessionSerializer

    def create(self, request, *args, **kwargs):
        self.handle_sessions()
        return super().create(request, *args, **kwargs)

    def handle_sessions(self):
        sessions_active = []
        for session_data in self.request.data.get("sessions", []):
            session_data["terminal"] = self.request.user.terminal.id
            _id = session_data["id"]
            session = get_object_or_none(Session, id=_id)
            if session:
                serializer = TerminalSessionSerializer(data=session_data,
                                                       instance=session)
            else:
                serializer = TerminalSessionSerializer(data=session_data)

            if serializer.is_valid():
                serializer.save()
            else:
                logger.error("session serializer is not valid {}".format(
                    serializer.errors))

            if not session_data["is_finished"]:
                sessions_active.append(session_data["id"])

        sessions_in_db_active = Session.objects.filter(
            is_finished=False, terminal=self.request.user.terminal.id
        )

        for session in sessions_in_db_active:
            if str(session.id) not in sessions_active:
                session.is_finished = True
                session.date_end = timezone.now()
                session.save()

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
    queryset = Session.objects.all()
    serializers_class = TerminalSessionSerializer
    permission_classes = (IsSuperUserOrAppUser,)

    def get_queryset(self):
        terminal_id = self.kwargs.get("terminal", None)
        if terminal_id:
            terminal = get_object_or_404(Terminal, id=terminal_id)
            self.queryset = terminal.terminalstatus_set.all()
        return self.queryset


class TerminalTaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
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


class SessionReplayAPI(APIView):
    permission_classes = (IsSuperUserOrAppUser,)

    def post(self, request, **kwargs):
        session_id = kwargs.get("pk", None)
        session = get_object_or_404(Session, id=session_id)
        record_dir = settings.CONFIG.SESSION_RECORDE_DIR
        date = session.date_start.strftime("%Y-%m-%d")
        record_dir = os.path.join(record_dir, date, str(session.id))
        record_filename = os.path.join(record_dir, "replay.tar.gz2")

        if not os.path.isdir(record_dir):
            try:
                os.makedirs(record_dir)
            except FileExistsError:
                pass

        archive_stream = request.data.get("archive")
        if not archive_stream:
            return Response("None file upload", status=400)

        with open(record_filename, 'wb') as f:
            for chunk in archive_stream.chunks():
                f.write(chunk)
        session.has_replay = True
        session.save()
        return Response({"session_id": session.id}, status=201)


class SessionCommandViewSet(viewsets.ViewSet):
    """接受app发送来的command log, 格式如下
    {
        "user": "admin",
        "asset": "localhost",
        "system_user": "web",
        "session": "xxxxxx",
        "input": "whoami",
        "output": "d2hvbWFp",  # base64.b64encode(s)
        "timestamp": 1485238673.0
    }

    """
    command_store = get_command_store()
    serializer_class = SessionCommandSerializer
    permission_classes = (IsSuperUserOrAppUser,)

    def get_queryset(self):
        self.command_store.all()

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, many=True)
        if serializer.is_valid():
            ok = self.command_store.bulk_save(serializer.validated_data)
            if ok:
                return Response("ok", status=201)
            else:
                return Response("save error", status=500)
        else:
            print(serializer.errors)
            return Response({"msg": "Not valid: {}".format(serializer.errors)}, status=401)

    def list(self, request, *args, **kwargs):
        queryset = list(self.command_store.all())
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
