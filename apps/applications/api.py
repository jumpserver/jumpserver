# -*- coding: utf-8 -*-
# 

from collections import OrderedDict
import copy
from rest_framework.generics import ListCreateAPIView
from rest_framework import viewsets
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view

from .models import Terminal, TerminalHeatbeat
from .serializers import TerminalSerializer, TerminalHeatbeatSerializer
from .hands import IsSuperUserOrAppUser, IsAppUser, ProxyLog, \
    IsSuperUserOrAppUserOrUserReadonly
from common.utils import get_object_or_none


class TerminalRegisterView(ListCreateAPIView):
    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        name = request.data.get('name', '')
        remote_addr = request.META.get('HTTP_X_REAL_IP') or \
                      request.META.get('REMOTE_ADDR')
        serializer = self.serializer_class(
            data={'name': name, 'remote_addr': remote_addr})

        if get_object_or_none(Terminal, name=name):
            return Response({'msg': 'Already register, Need '
                                    'administrator active it'}, status=200)

        if serializer.is_valid():
            terminal = serializer.save()
            app_user, access_key = terminal.create_related_app_user()
            data = OrderedDict()
            data['terminal'] = copy.deepcopy(serializer.data)
            data['user'] = app_user.to_json()
            data['access_key_id'] = access_key.id
            data['access_key_secret'] = access_key.secret
            return Response(data, status=201)
        else:
            data = {'msg': 'Not valid', 'detail': ';'.join(serializer.errors)}
            return Response(data, status=400)

    def list(self, request, *args, **kwargs):
        return Response('', status=404)


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer
    permission_classes = (IsSuperUserOrAppUserOrUserReadonly,)

    def create(self, request, *args, **kwargs):
        return Response({'msg': 'Use register view except that'}, status=404)

    # def destroy(self, request, *args, **kwargs):
        # instance = self.get_object()
        # if instance.user is not None:
        #     instance.user.delete()
        # return super(TerminalViewSet, self).destroy(request, *args, **kwargs)

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
