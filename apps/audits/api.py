# ~*~ coding: utf-8 ~*~
# 


from rest_framework import generics

import serializers

from .models import ProxyLog, CommandLog
from .hands import IsSuperUserOrTerminalUser, Terminal


class ProxyLogListCreateApi(generics.ListCreateAPIView):
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

    queryset = ProxyLog.objects.all()
    serializer_class = serializers.ProxyLogSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)

    def perform_create(self, serializer):
        # Todo: May be save log_file
        super(ProxyLogListCreateApi, self).perform_create(serializer)


class ProxyLogDetailApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProxyLog.objects.all()
    serializer_class = serializers.ProxyLogSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)


class CommandLogCreateApi(generics.ListCreateAPIView):
    queryset = CommandLog.objects.all()
    serializer_class = serializers.CommandLogSerializer
    permission_classes = (IsSuperUserOrTerminalUser,)
