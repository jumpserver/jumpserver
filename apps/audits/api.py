# ~*~ coding: utf-8 ~*~
# 


from __future__ import absolute_import, unicode_literals
from rest_framework import generics, viewsets
from rest_framework.views import APIView, Response

from . import models, serializers
from .hands import IsSuperUserOrTerminalUser, Terminal


class ProxyLogViewSet(viewsets.ModelViewSet):
    """User proxy to backend server need call this api.

    params: {
        "username": "",
        "name": "",
        "hostname": "",
        "ip": "",
        "terminal", "",
        "login_type": "",
        "system_user": "",
        "was_failed": "",
        "date_start": ""
    }

    some params we need generate:  {
        "log_file", "", # No use now, may be think more about monitor and record
    }
    """

    queryset = models.ProxyLog.objects.all()
    serializer_class = serializers.ProxyLogSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)


class CommandLogViewSet(viewsets.ModelViewSet):
    queryset = models.CommandLog.objects.all()
    serializer_class = serializers.CommandLogSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)


# class CommandLogTitleApi(APIView):
#     def get(self, request):
#         response = [
#             {"name": "command_no", "title": "ID", "type": "number"},
#             {"name": "command", "title": "Title", "visible": True, "filterable": True},
#             {"name": "datetime", "title": "Datetime", "type"},
#             {"name": "output", "title": "Output", "filterable": True},
#         ]
#