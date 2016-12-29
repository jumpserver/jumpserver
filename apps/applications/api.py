# -*- coding: utf-8 -*-
# 

from django.core.cache import cache
from django.conf import settings
import copy
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import viewsets
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view

from .models import Terminal, TerminalHeatbeat
from .serializers import TerminalSerializer, TerminalHeatbeatSerializer
from .hands import IsSuperUserOrAppUser, IsAppUser, User
from common.utils import get_object_or_none


class TerminalRegisterView(ListCreateAPIView):
    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        name = request.data.get('name', '')
        remote_addr = request.META.get('X-Real-IP') or request.META.get('REMOTE_ADDR')
        serializer = self.serializer_class(data={'name': name, 'remote_addr': remote_addr})

        if get_object_or_none(Terminal, name=name):
            return Response({'msg': 'Registed, Need admin active it'}, status=200)

        if serializer.is_valid():
            terminal = serializer.save()
            app_user, access_key = terminal.create_related_app_user()
            data = {}
            data['applications'] = copy.deepcopy(serializer.data)
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
    permission_classes = (IsSuperUserOrAppUser,)

    def create(self, request, *args, **kwargs):
        return Response({'msg': 'Use register view except that'}, status=404)


class TerminalHeatbeatViewSet(viewsets.ModelViewSet):
    queryset = TerminalHeatbeat.objects.all()
    serializer_class = TerminalHeatbeatSerializer
    permission_classes = (IsAppUser,)

    def create(self, request, *args, **kwargs):
        terminal = request.user.terminal
        TerminalHeatbeat.objects.create(terminal=terminal)
        return Response({'msg': 'Success'}, status=201)
