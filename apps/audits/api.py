# ~*~ coding: utf-8 ~*~
# 


from __future__ import absolute_import, unicode_literals

from rest_framework import generics, viewsets
from rest_framework_bulk import BulkModelViewSet

from audits.backends import command_store
from audits.backends.command.serializers import CommandLogSerializer
from . import models, serializers
from .hands import IsSuperUserOrAppUser, IsAppUser


class ProxyLogReceiveView(generics.CreateAPIView):
    queryset = models.ProxyLog.objects.all()
    serializer_class = serializers.ProxyLogSerializer
    permission_classes = (IsAppUser,)

    def get_serializer(self, *args, **kwargs):
        kwargs['data']['terminal'] = self.request.user.terminal.name
        return super(ProxyLogReceiveView, self).get_serializer(*args, **kwargs)


class ProxyLogViewSet(viewsets.ModelViewSet):
    """User proxy to backend server need call this api.

    params: {
        "username": "",
        "name": "",
        "hostname": "",
        "ip": "",
        "terminal": "",
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
    permission_classes = (IsSuperUserOrAppUser,)


class CommandLogViewSet(BulkModelViewSet):
    """接受app发送来的command log, 格式如下
    {
        "proxy_log_id": 23,
        "user": "admin",
        "asset": "localhost",
        "system_user": "web",
        "command_no": 1,
        "command": "whoami",
        "output": "d2hvbWFp",  # base64.b64encode(s)
        "timestamp": 1485238673.0
    }

    """
    queryset = command_store.all()
    serializer_class = CommandLogSerializer
    permission_classes = (IsSuperUserOrAppUser,)

