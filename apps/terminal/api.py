# -*- coding: utf-8 -*-
# 

from django.core.cache import cache
from django.conf import settings
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import viewsets
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny

from common.utils import signer, get_object_or_none
from .models import Terminal, TerminalHeatbeat
from .serializers import TerminalSerializer, TerminalHeatbeatSerializer
from .hands import IsSuperUserOrTerminalUser, User



class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        name = signer.unsign(request.data.get('name', ''))
        if name:
            terminal = get_object_or_none(Terminal, name=name)
            if terminal:
                data = {
                    'data': {'name': name, 'id': terminal.id},
                }
                if terminal.is_active:
                    data['msg'] = 'Success'
                    return Response(data=data, status=200)
                else:
                    data['msg'] = 'Need admin active this terminal'
                    return Response(data=data, status=203)

            else:
                ip = request.META.get('X-Real-IP') or request.META.get('REMOTE_ADDR')
                terminal = Terminal.objects.create(name=name, ip=ip)
                data = {
                    'data': {'name': name, 'id': terminal.id},
                    'msg': 'Need admin active this terminal',
                }
                return Response(data=data, status=201)
        else:
            return Response(data={'msg': 'Secrete key invalid'}, status=401)


class TerminalHeatbeatApi(ListCreateAPIView):
    queryset = TerminalHeatbeat.objects.all()
    serializer_class = TerminalHeatbeatSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)


class TerminalHeatbeatViewSet(viewsets.ModelViewSet):
    queryset = TerminalHeatbeat.objects.all()
    serializer_class = TerminalHeatbeatSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)

    def create(self, request, *args, **kwargs):
        terminal = request.user
        TerminalHeatbeat.objects.create(terminal=terminal)
        return Response({'msg': 'Success'})

