# -*- coding: utf-8 -*-
# 

from django.core.cache import cache
from django.conf import settings
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView, Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny

from common.utils import signer, get_object_or_none
from .models import Terminal, HeatbeatFailedLog
from .serializers import TerminalSerializer, TerminalHeatbeatSerializer
from .hands import IsSuperUserOrTerminalUser


class TerminalViewSet(ModelViewSet):
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


class TerminalHeatbeatApi(APIView):
    # model = HeatbeatFailedLog
    # serializer_class = TerminalHeatbeatSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)

    def put(self, request, *args, **kwargs):
        terminal_id = request.user.id
        cache.set('terminal_heatbeat_%s' % terminal_id, settings.CONFIG.TERMINAL_HEATBEAT_INTERVAL * 3)
        return Response({'msg': 'Success'})


# class TerminalApiDetailUpdateDetailApi(RetrieveUpdateDestroyAPIView):
#     queryset = Terminal.objects.all()
#     serializer_class = TerminalSerializer
#     permission_classes = (IsSuperUserOrTerminalUser,)
