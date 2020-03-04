# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404, reverse
from django.core.files.storage import default_storage
from rest_framework import viewsets
from rest_framework.response import Response

from common.utils import is_uuid, get_logger
from common.mixins.api import AsyncApiMixin
from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor
from common.drf.filters import DatetimeRangeFilter
from orgs.mixins.api import OrgBulkModelViewSet
from ..utils import find_session_replay_local, download_session_replay
from ..hands import SystemUser
from ..models import Session
from .. import serializers


__all__ = ['SessionViewSet', 'SessionReplayViewSet',]
logger = get_logger(__name__)


class SessionViewSet(OrgBulkModelViewSet):
    model = Session
    serializer_classes = {
        'default': serializers.SessionSerializer,
        'display': serializers.SessionDisplaySerializer,
    }
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


class SessionReplayViewSet(AsyncApiMixin, viewsets.ViewSet):
    serializer_class = serializers.ReplaySerializer
    permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor,)
    session = None
    download_cache_key = "SESSION_REPLAY_DOWNLOAD_{}"

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

    @staticmethod
    def get_replay_data(session, url):
        tp = 'json'
        if session.protocol in ('rdp', 'vnc'):
            tp = 'guacamole'

        download_url = reverse('terminal:session-replay-download', kwargs={'pk': session.id})
        data = {
            'type': tp, 'src': url,
            'user': session.user, 'asset': session.asset,
            'system_user': session.system_user,
            'date_start': session.date_start,
            'date_end': session.date_end,
            'download_url': download_url,
        }
        return data

    def is_need_async(self):
        if self.action != 'retrieve':
            return False
        return True

    def retrieve(self, request, *args, **kwargs):
        session_id = kwargs.get('pk')
        session = get_object_or_404(Session, id=session_id)
        local_path, url = find_session_replay_local(session)

        if not local_path:
            local_path, url = download_session_replay(session)
            if not local_path:
                return Response({"error": url})
        data = self.get_replay_data(session, url)
        return Response(data)
