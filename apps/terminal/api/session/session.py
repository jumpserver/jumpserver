# -*- coding: utf-8 -*-
#
import os
import tarfile
from django.core.files.storage import default_storage
from django.db.models import F
from django.http import FileResponse
from django.shortcuts import get_object_or_404, reverse
from django.utils.encoding import escape_uri_path
from django.utils.translation import ugettext as _
from django_filters import rest_framework as filters
from rest_framework import generics
from rest_framework import viewsets, views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.drf.filters import BaseFilterSet
from common.const.http import GET
from common.drf.filters import DatetimeRangeFilter
from common.drf.renders import PassthroughRenderer
from common.api import AsyncApiMixin
from common.utils import data_to_json, is_uuid
from common.utils import get_logger, get_object_or_none
from common.storage.replay import ReplayStorageHandler
from rbac.permissions import RBACPermission
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import tmp_to_root_org, tmp_to_org
from terminal import serializers
from terminal.models import Session
from terminal.utils import is_session_approver
from terminal.permissions import IsSessionAssignee
from users.models import User

__all__ = [
    'SessionViewSet', 'SessionReplayViewSet',
    'SessionJoinValidateAPI', 'MySessionAPIView',
]

logger = get_logger(__name__)


class MySessionAPIView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.SessionSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Session.objects.filter(user_id=user.id)
        return qs


class SessionFilterSet(BaseFilterSet):
    terminal = filters.CharFilter(method='filter_terminal')

    class Meta:
        model = Session
        fields = [
            "user", "asset", "account", "remote_addr",
            "protocol", "is_finished", 'login_from', 'terminal'
        ]

    @staticmethod
    def filter_terminal(queryset, name, value):
        if is_uuid(value):
            return queryset.filter(terminal__id=value)
        else:
            return queryset.filter(terminal__name=value)


class SessionViewSet(OrgBulkModelViewSet):
    model = Session
    serializer_classes = {
        'default': serializers.SessionSerializer,
        'display': serializers.SessionDisplaySerializer,
    }
    search_fields = [
        "user", "asset", "account", "remote_addr",
        "protocol", "is_finished", 'login_from',
    ]
    filterset_class = SessionFilterSet
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    extra_filter_backends = [DatetimeRangeFilter]
    rbac_perms = {
        'download': ['terminal.download_sessionreplay']
    }
    permission_classes = [RBACPermission | IsSessionAssignee]

    @staticmethod
    def prepare_offline_file(session, local_path):
        replay_path = default_storage.path(local_path)
        current_dir = os.getcwd()
        dir_path = os.path.dirname(replay_path)
        replay_filename = os.path.basename(replay_path)
        meta_filename = '{}.json'.format(session.id)
        offline_filename = '{}.tar'.format(session.id)
        os.chdir(dir_path)

        with open(meta_filename, 'wt') as f:
            serializer = serializers.SessionDisplaySerializer(session)
            data = data_to_json(serializer.data)
            f.write(data)

        with tarfile.open(offline_filename, 'w') as f:
            f.add(replay_filename)
            f.add(meta_filename)
        file = open(offline_filename, 'rb')
        os.chdir(current_dir)
        return file

    def get_storage(self):
        return ReplayStorageHandler(self.get_object())

    @action(methods=[GET], detail=True, renderer_classes=(PassthroughRenderer,), url_path='replay/download',
            url_name='replay-download')
    def download(self, request, *args, **kwargs):
        storage = self.get_storage()
        local_path, url_or_err = storage.get_file_path_url()
        if local_path is None:
            return Response({'error': url_or_err}, status=404)

        file = self.prepare_offline_file(storage.obj, local_path)
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        # 这里要注意哦，网上查到的方法都是response['Content-Disposition']='attachment;filename="filename.py"',
        # 但是如果文件名是英文名没问题，如果文件名包含中文，下载下来的文件名会被改为url中的path。
        filename = escape_uri_path('{}.tar'.format(storage.obj.id))
        disposition = "attachment; filename*=UTF-8''{}".format(filename)
        response["Content-Disposition"] = disposition
        return response

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('terminal') \
            .annotate(terminal_display=F('terminal__name'))
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # 解决guacamole更新session时并发导致幽灵会话的问题，暂不处理
        if self.request.method in ('PATCH',):
            queryset = queryset.select_for_update()
        return queryset

    def perform_create(self, serializer):
        if hasattr(self.request.user, 'terminal'):
            serializer.validated_data["terminal"] = self.request.user.terminal
        return super().perform_create(serializer)


class SessionReplayViewSet(AsyncApiMixin, viewsets.ViewSet):
    serializer_class = serializers.ReplaySerializer
    download_cache_key = "SESSION_REPLAY_DOWNLOAD_{}"
    session = None
    rbac_perms = {
        'create': 'terminal.upload_sessionreplay',
        'retrieve': 'terminal.view_sessionreplay',
    }

    def create(self, request, *args, **kwargs):
        session_id = kwargs.get('pk')
        session = get_object_or_404(Session, id=session_id)
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']
            # 兼容旧版本 API 未指定 version 为 2 的情况
            version = serializer.validated_data.get('version', 2)
            name, err = session.save_replay_to_storage_with_version(file, version)
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
            # 需要考虑录像播放和离线播放器的约定，暂时不处理
            tp = 'guacamole'
        if url.endswith('.cast.gz'):
            tp = 'asciicast'
        if url.endswith('.replay.mp4'):
            tp = 'mp4'

        download_url = reverse('api-terminal:session-replay-download', kwargs={'pk': session.id})
        data = {
            'type': tp, 'src': url,
            'user': session.user, 'asset': session.asset,
            'account': session.account,
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

        storage = ReplayStorageHandler(session)
        local_path, url_or_err = storage.get_file_path_url()
        if local_path is None:
            return Response({"error": url_or_err}, status=404)
        data = self.get_replay_data(session, local_path)
        return Response(data)


class SessionJoinValidateAPI(views.APIView):
    """
    监控用
    """
    serializer_class = serializers.SessionJoinValidateSerializer
    rbac_perms = {
        'POST': 'terminal.validate_sessionactionperm'
    }

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            msg = str(serializer.errors)
            return Response({'ok': False, 'msg': msg}, status=401)
        user_id = serializer.validated_data['user_id']
        session_id = serializer.validated_data['session_id']

        with tmp_to_root_org():
            session = get_object_or_none(Session, pk=session_id)
        if not session:
            msg = _('Session does not exist: {}'.format(session_id))
            return Response({'ok': False, 'msg': msg}, status=401)
        if not session.can_join:
            msg = _('Session is finished or the protocol not supported')
            return Response({'ok': False, 'msg': msg}, status=401)

        user = get_object_or_none(User, pk=user_id)
        if not user:
            msg = _('User does not exist: {}'.format(user_id))
            return Response({'ok': False, 'msg': msg}, status=401)

        with tmp_to_org(session.org):
            if is_session_approver(session_id, user_id):
                return Response({'ok': True, 'msg': ''}, status=200)

            if not user.has_perm('terminal.monitor_session'):
                msg = _('User does not have permission')
                return Response({'ok': False, 'msg': msg}, status=401)

        return Response({'ok': True, 'msg': ''}, status=200)
