# -*- coding: utf-8 -*-
#
import logging
import os

from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.http import HttpResponseNotFound
from django.conf import settings
from rest_framework.pagination import LimitOffsetPagination
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
import jms_storage


from common.utils import is_uuid
from common.permissions import IsOrgAdminOrAppUser
from ..hands import SystemUser
from ..models import Terminal, Session
from .. import serializers
from ..backends import get_command_storage, get_multi_command_storage, \
    SessionCommandSerializer

__all__ = ['SessionViewSet', 'SessionReplayViewSet', 'CommandViewSet']
logger = logging.getLogger(__file__)


class SessionViewSet(BulkModelViewSet):
    queryset = Session.objects.all()
    serializer_class = serializers.SessionSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_queryset(self):
        queryset = super().get_queryset()
        terminal_id = self.kwargs.get("terminal", None)
        if terminal_id:
            terminal = get_object_or_404(Terminal, id=terminal_id)
            queryset = queryset.filter(terminal=terminal)
            return queryset
        return queryset

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'terminal'):
            serializer.validated_data["terminal"] = self.request.user.terminal
        sid = serializer.validated_data["system_user"]
        # guacamole提交的是id
        if is_uuid(sid):
            _system_user = SystemUser.get_system_user_by_id_or_cached(sid)
            if _system_user:
                serializer.validated_data["system_user"] = _system_user.name
        return super().perform_create(serializer)


class CommandViewSet(viewsets.ViewSet):
    """接受app发送来的command log, 格式如下
    {
        "user": "admin",
        "asset": "localhost",
        "system_user": "web",
        "session": "xxxxxx",
        "input": "whoami",
        "output": "d2hvbWFp",  # base64.b64encode(s)
        "timestamp": 1485238673.0
    }

    """
    command_store = get_command_storage()
    serializer_class = SessionCommandSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_queryset(self):
        self.command_store.filter(**dict(self.request.query_params))

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, many=True)
        if serializer.is_valid():
            ok = self.command_store.bulk_save(serializer.validated_data)
            if ok:
                return Response("ok", status=201)
            else:
                return Response("Save error", status=500)
        else:
            msg = "Command not valid: {}".format(serializer.errors)
            logger.error(msg)
            return Response({"msg": msg}, status=401)

    def list(self, request, *args, **kwargs):
        multi_command_storage = get_multi_command_storage()
        queryset = multi_command_storage.filter()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)


class SessionReplayViewSet(viewsets.ViewSet):
    serializer_class = serializers.ReplaySerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    session = None

    def create(self, request, *args, **kwargs):
        session_id = kwargs.get('pk')
        session = get_object_or_404(Session, id=session_id)
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']
            name, err = session.save_to_storage(file)
            if not name:
                msg = "Failed save replay `{}`: {}".format(session_id, err)
                logger.error(msg)
                return Response({'msg': str(err)}, status=400)
            url = default_storage.url(name)
            return Response({'url': url}, status=201)
        else:
            msg = 'Upload data invalid: {}'.format(serializer.errors)
            logger.error(msg)
            return Response({'msg': serializer.errors}, status=401)

    def retrieve(self, request, *args, **kwargs):
        session_id = kwargs.get('pk')
        session = get_object_or_404(Session, id=session_id)

        tp = 'json'
        if session.protocol in ('rdp', 'vnc'):
            tp = 'guacamole'

        data = {'type': tp, 'src': ''}

        # 新版本和老版本的文件后缀不同
        session_path = session.get_rel_replay_path()  # 存在外部存储上的路径
        local_path = session.get_local_path()
        local_path_v1 = session.get_local_path(version=1)

        # 去default storage中查找
        for _local_path in (local_path, local_path_v1, session_path):
            if default_storage.exists(_local_path):
                url = default_storage.url(_local_path)
                data['src'] = url
                return Response(data)

        # 去定义的外部storage查找
        configs = settings.TERMINAL_REPLAY_STORAGE
        configs = {k: v for k, v in configs.items() if v['TYPE'] != 'server'}
        if not configs:
            return HttpResponseNotFound()

        target_path = os.path.join(default_storage.base_location, local_path)   # 保存到storage的路径
        target_dir = os.path.dirname(target_path)
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        storage = jms_storage.get_multi_object_storage(configs)
        ok, err = storage.download(session_path, target_path)
        if not ok:
            logger.error("Failed download replay file: {}".format(err))
            return HttpResponseNotFound()
        data['src'] = default_storage.url(local_path)
        return Response(data)

