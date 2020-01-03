# -*- coding: utf-8 -*-
#
import os

from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.http import HttpResponseNotFound
from django.conf import settings
from rest_framework import viewsets
from rest_framework.response import Response
import jms_storage

from common.utils import is_uuid, get_logger
from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor
from common.drf.filters import DatetimeRangeFilter
from orgs.mixins.api import OrgBulkModelViewSet
from ..hands import SystemUser
from ..models import Session, ReplayStorage
from .. import serializers


__all__ = ['SessionViewSet', 'SessionReplayViewSet',]
logger = get_logger(__name__)


class SessionViewSet(OrgBulkModelViewSet):
    model = Session
    serializer_class = serializers.SessionSerializer
    permission_classes = (IsOrgAdminOrAppUser, )
    filterset_fields = [
        "user", "asset", "system_user", "remote_addr",
        "protocol", "terminal", "is_finished",
    ]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    extra_filter_backends = [DatetimeRangeFilter]

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # 解决guacamole更新session时并发导致幽灵会话的问题
        if self.request.method in ('PATCH',):
            queryset = queryset.select_for_update()
        return queryset

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'terminal'):
            serializer.validated_data["terminal"] = self.request.user.terminal
        sid = serializer.validated_data["system_user"]
        # guacamole提交的是id
        if is_uuid(sid):
            _system_user = get_object_or_404(SystemUser, id=sid)
            serializer.validated_data["system_user"] = _system_user.name
        return super().perform_create(serializer)

    def get_permissions(self):
        if self.request.method.lower() in ['get']:
            self.permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor, )
        return super().get_permissions()


class SessionReplayViewSet(viewsets.ViewSet):
    serializer_class = serializers.ReplaySerializer
    permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor,)
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

        replay_storages = ReplayStorage.objects.all()
        configs = {
            storage.name: storage.config
            for storage in replay_storages
            if not storage.in_defaults()
        }
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

