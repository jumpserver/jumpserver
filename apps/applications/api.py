# -*- coding: utf-8 -*-
# 

from collections import OrderedDict
import copy
from rest_framework import viewsets
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from .models import Terminal, TerminalHeatbeat
from .serializers import TerminalSerializer, TerminalHeatbeatSerializer
from .hands import IsSuperUserOrAppUser, IsAppUser, ProxyLog, \
    IsSuperUserOrAppUserOrUserReadonly
from common.utils import get_object_or_none


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.all()
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
            app_user, access_key = terminal.create_related_app_user()
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


tasks = OrderedDict()
# tasks = {1: [{'name': 'kill_proxy', 'proxy_log_id': 23}]}


class TerminalHeatbeatViewSet(viewsets.ModelViewSet):
    queryset = TerminalHeatbeat.objects.all()
    serializer_class = TerminalHeatbeatSerializer
    permission_classes = (IsAppUser,)

    def create(self, request, *args, **kwargs):
        terminal = request.user.terminal
        TerminalHeatbeat.objects.create(terminal=terminal)
        task = tasks.get(terminal.name)
        tasks[terminal.name] = []
        return Response({'msg': 'Success',
                         'tasks': task},
                        status=201)


class TerminateConnectionView(APIView):
    def post(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            data = [request.data]
        else:
            data = request.data
        for d in data:
            proxy_log_id = d.get('proxy_log_id')
            proxy_log = get_object_or_404(ProxyLog, id=proxy_log_id)
            terminal_id = proxy_log.terminal
            if terminal_id in tasks:
                tasks[terminal_id].append({'name': 'kill_proxy',
                                           'proxy_log_id': proxy_log_id})
            else:
                tasks[terminal_id] = [{'name': 'kill_proxy',
                                       'proxy_log_id': proxy_log_id}]

        return Response({'msg': 'get it'})
