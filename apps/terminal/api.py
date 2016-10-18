# -*- coding: utf-8 -*-
# 

from rest_framework.generics import ListCreateAPIView
from rest_framework.views import APIView, Response
from rest_framework.permissions import AllowAny

from common.utils import unsign, get_object_or_none
from .models import Terminal
from .serializers import TerminalSerializer


class TerminalApi(ListCreateAPIView):
    queryset = Terminal.objects.all()
    serializer_class = TerminalSerializer
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        name = unsign(request.data.get('name', ''))
        if name:
            terminal = get_object_or_none(Terminal, name=name)
            if terminal:
                if terminal.is_accepted and terminal.is_active:
                    return Response(data={'data': {'name': name, 'ip': terminal.ip},
                                          'msg': 'Success'},
                                    status=200)
                else:
                    return Response(data={'data': {'name': name, 'ip': terminal.ip},
                                          'msg': 'Need admin accept or active it'},
                                    status=203)

            else:
                ip = request.META.get('X-Real-IP') or request.META.get('REMOTE_ADDR')
                terminal = Terminal.objects.create(name=name, ip=ip)
                return Response(data={'data': {'name': name, 'ip': terminal.ip},
                                      'msg': 'Need admin accept or active it'},
                                status=204)
        else:
            return Response(data={'error': 'Secrete key invalid'}, status=401)


# class TerminalRegister(APIView):
#     def post(self, request, format='json'):
#         return Response(data={'hello': request.META.get('REMOTE_ADDR')})
#         name = unsign(request.data.get('name', ''))
#         if name:
#             terminal = get_object_or_none(Terminal, name=name)
#             if terminal:
#                 return Response(data={'name': name, 'ip': terminal.ip}, status=200)
#             else:
#                 ip = request.Meta.get('X-Real-IP')
#                 Terminal.objects.create(name=name, ip=request.META.host)



