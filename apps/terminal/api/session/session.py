# -*- coding: utf-8 -*-
#
import os
import tarfile
import zipfile

from six import BytesIO

from django.core.files.storage import default_storage
from django.core.cache import cache
from django.conf import settings
from django.db.models import F
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, reverse
from django.utils.encoding import escape_uri_path
from django.utils.translation import ugettext as _
from rest_framework import generics
from rest_framework import viewsets, views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.const.http import GET
from common import const
from common.drf.filters import DatetimeRangeFilter
from common.drf.renders import PassthroughRenderer
from common.mixins.api import AsyncApiMixin
from common.utils import get_logger, get_object_or_none, data_to_json
from common.utils.timezone import local_now_display
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import tmp_to_root_org, tmp_to_org
from terminal import serializers
from terminal.models import Session
from terminal.utils import (
    find_session_replay_local, download_session_replay,
    is_session_approver, get_sessions_replay_url
)
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
    filterset_fields = search_fields + ['terminal']
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    extra_filter_backends = [DatetimeRangeFilter]
    rbac_perms = {
        'download': ['terminal.download_sessionreplay']
    }

    @staticmethod
    def _gen_replay_file(sessions):
        file_total_size = 0
        file_path = []
        for session in sessions:
            local_path = session.pop('local_path')
            replay_path = default_storage.path(local_path)
            dir_path = os.path.dirname(replay_path)
            replay_filename = os.path.basename(replay_path)
            meta_filename = '{}.json'.format(session['id'])
            offline_filename = '{}.tar'.format(session['id'])
            os.chdir(dir_path)

            with open(meta_filename, 'wt') as f:
                f.write(data_to_json(session))

            with tarfile.open(offline_filename, 'w') as f:
                f.add(replay_filename)
                f.add(meta_filename)
            file_total_size += os.path.getsize(offline_filename)
            file_path.append(os.path.join(dir_path, offline_filename))
        return file_total_size, file_path

    def prepare_offline_file(self, sessions):
        file_obj = {'error': None, 'file': None, 'file_num': 0}
        current_dir = os.getcwd()

        file_total_size, file_path_list = self._gen_replay_file(sessions)
        if (file_total_size / 1024 ** 2) > settings.DOWNLOAD_MEMORY_LIMIT:
            file_obj['error'] = _(
                'The selected resources exceeded the system limit. '
                'Procedure Adjust resources or contact the Administrator'
            )
        else:
            zip_file_io = BytesIO()
            zf = zipfile.ZipFile(
                zip_file_io, 'a', zipfile.ZIP_DEFLATED, False
            )
            for f in file_path_list:
                zf.write(f, os.path.basename(f))
            zf.close()
            zip_file_io.seek(0)
            file_obj['file'] = zip_file_io.read()
            file_obj['file_num'] = len(sessions)
        os.chdir(current_dir)
        return file_obj

    def get_objects(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = self.kwargs.get(lookup_url_kwarg)
        ids = cache.get(const.KEY_CACHE_RESOURCE_IDS.format(pk)) if pk else None
        if not ids:
            ids = [pk]

        sessions = self.model.objects.filter(id__in=ids)
        return sessions

    @action(methods=[GET], detail=True, renderer_classes=(PassthroughRenderer,), url_path='replay/download',
            url_name='replay-download')
    def download(self, request, *args, **kwargs):
        sessions = self.get_objects()
        sessions_info = get_sessions_replay_url(sessions)
        if sessions_info['error']:
            return JsonResponse({"error": ','.join(sessions_info['error'])}, status=404)

        file_obj = self.prepare_offline_file(sessions_info['data'])
        if file_obj['error']:
            return JsonResponse({"error": file_obj['error']}, status=403)

        file, file_num = file_obj['file'], file_obj['file_num']
        filename_prefix = 'REPLAY-SET-{}'.format(local_now_display('%Y-%m-%d-%H-%M-%S'))
        filename = escape_uri_path('{}-[{}-ITEMS]'.format(filename_prefix, file_num))

        response = HttpResponse(file, content_type='application/zip', charset='utf-8')
        disposition = 'attachment;filename={filename}.zip'.format(filename=filename)
        response['Content-Disposition'] = disposition
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

        download_url = reverse('api-terminal:session-replay-download', kwargs={'pk': session.id})
        data = {
            'type': tp, 'src': url,
            'user': session.user, 'asset': session.asset,
            'system_user': session.account,
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
                return Response({"error": url}, status=404)
        data = self.get_replay_data(session, url)
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
