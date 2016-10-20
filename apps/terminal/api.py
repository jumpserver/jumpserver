# -*- coding: utf-8 -*-
# 

from rest_framework.generics import ListCreateAPIView, CreateAPIView
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny

from common.utils import unsign, get_object_or_none
from .models import Terminal, TerminalHeatbeat
from .serializers import TerminalSerializer, TerminalHeatbeatSerializer
from .hands import IsSuperUserOrTerminalUser


class TerminalCreateListApi(ListCreateAPIView):
    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        name = unsign(request.data.get('name', ''))
        print(name)
        if name:
            terminal = get_object_or_none(Terminal, name=name)
            if terminal:
                if terminal.is_active:
                    return Response(data={'data': {'name': name, 'id': terminal.id},
                                          'msg': 'Success'},
                                    status=200)
                else:
                    return Response(data={'data': {'name': name, 'ip': terminal.ip},
                                          'msg': 'Need admin active it'},
                                    status=203)

            else:
                ip = request.META.get('X-Real-IP') or request.META.get('REMOTE_ADDR')
                terminal = Terminal.objects.create(name=name, ip=ip)
                return Response(data={'data': {'name': name, 'ip': terminal.ip},
                                      'msg': 'Need admin active it'},
                                status=204)
        else:
            return Response(data={'msg': 'Secrete key invalid'}, status=401)


class TerminalHeatbeatApi(CreateAPIView):
    model = TerminalHeatbeat
    serializer_class = TerminalHeatbeatSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)
