# -*- coding: utf-8 -*-
#
import os
import tarfile

from django.core.files.storage import default_storage
from django.db.models import F
from django.http import FileResponse
from django.shortcuts import get_object_or_404, reverse
from django.utils.encoding import escape_uri_path
from django.utils.translation import gettext_noop, gettext as _
from django_filters import rest_framework as filters
from rest_framework import generics
from rest_framework import viewsets, views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audits.const import ActionChoices
from common.api import AsyncApiMixin
from common.const.http import GET, POST
from common.drf.filters import BaseFilterSet
from common.drf.filters import DatetimeRangeFilterBackend
from common.drf.renders import PassthroughRenderer
from common.permissions import IsServiceAccount
from common.storage.replay import ReplayStorageHandler
from common.utils import data_to_json, is_uuid, i18n_fmt
from common.utils import get_logger, get_object_or_none
from common.views.mixins import RecordViewLogMixin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import tmp_to_root_org, tmp_to_org
from rbac.permissions import RBACPermission
from terminal import serializers
from terminal.const import TerminalType
from terminal.models import Session
from terminal.permissions import IsSessionAssignee
from terminal.session_lifecycle import lifecycle_events_map, reasons_map
from terminal.utils import is_session_approver
from users.models import User

__all__ = [
    'SessionViewSet', 'SessionReplayViewSet',
    'SessionJoinValidateAPI', 'MySessionAPIView'
]

logger = get_logger(__name__)

REPLAY_OP = gettext_noop('User %s %s session %s replay')


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
            "user", "user_id", "asset", "asset_id", "account", "remote_addr",
            "protocol", "is_finished", 'login_from', 'terminal'
        ]

    @staticmethod
    def filter_terminal(queryset, name, value):
        if is_uuid(value):
            return queryset.filter(terminal__id=value)
        else:
            return queryset.filter(terminal__name=value)


class SessionViewSet(RecordViewLogMixin, OrgBulkModelViewSet):
    model = Session
    serializer_classes = {
        'default': serializers.SessionSerializer,
        'display': serializers.SessionDisplaySerializer,
        'lifecycle_log': serializers.SessionLifecycleLogSerializer,
    }
    search_fields = [
        "user", "asset", "account", "remote_addr",
        "protocol", "is_finished", 'login_from',
    ]
    filterset_class = SessionFilterSet
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    extra_filter_backends = [DatetimeRangeFilterBackend]
    rbac_perms = {
        'download': ['terminal.download_sessionreplay'],
    }
    permission_classes = [RBACPermission]

    def get_permissions(self):
        if self.action == 'retrieve':
            self.permission_classes = [RBACPermission | IsSessionAssignee]
        return super().get_permissions()

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
        local_path, url = storage.get_file_path_url()
        if local_path is None:
            # url => error message
            return Response({'error': url}, status=404)

        file = self.prepare_offline_file(storage.obj, local_path)
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        # 这里要注意哦，网上查到的方法都是response['Content-Disposition']='attachment;filename="filename.py"',
        # 但是如果文件名是英文名没问题，如果文件名包含中文，下载下来的文件名会被改为url中的path。
        filename = escape_uri_path('{}.tar'.format(storage.obj.id))
        disposition = "attachment; filename*=UTF-8''{}".format(filename)
        response["Content-Disposition"] = disposition

        detail = i18n_fmt(
            REPLAY_OP, self.request.user, _('Download'), str(storage.obj)
        )
        self.record_logs(
            [storage.obj.asset_id], ActionChoices.download, detail,
            model=Session, resource_display=str(storage.obj)
        )
        return response

    @action(methods=[GET], detail=False, permission_classes=[IsAuthenticated], url_path='online-info', )
    def online_info(self, request, *args, **kwargs):
        asset = self.request.query_params.get('asset_id')
        account = self.request.query_params.get('account')
        if asset is None or account is None:
            return Response({'count': None})

        queryset = Session.objects.filter(is_finished=False) \
            .filter(asset_id=asset) \
            .filter(protocol='rdp')  # 当前只统计 rdp 协议的会话
        if '(' in account and ')' in account:
            queryset = queryset.filter(account=account)
        else:
            queryset = queryset.filter(account__endswith='({})'.format(account))
        count = queryset.count()
        return Response({'count': count})

    @action(methods=[POST], detail=True, permission_classes=[IsServiceAccount], url_path='lifecycle_log',
            url_name='lifecycle_log')
    def lifecycle_log(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        event = validated_data.pop('event', None)
        event_class = lifecycle_events_map.get(event, None)
        if not event_class:
            return Response({'msg': f'event_name {event} invalid'}, status=400)
        session = self.get_object()
        reason = validated_data.pop('reason', None)
        reason = reasons_map.get(reason, reason)
        event_obj = event_class(session, reason, **validated_data)
        activity_log = event_obj.create_activity_log()
        return Response({'msg': 'ok', 'id': activity_log.id})

    def get_queryset(self):
        queryset = super().get_queryset() \
            .prefetch_related('terminal') \
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


class SessionReplayViewSet(AsyncApiMixin, RecordViewLogMixin, viewsets.ViewSet):
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
        all_guacamole_types = (
            TerminalType.lion, TerminalType.guacamole,
            TerminalType.razor, TerminalType.xrdp
        )

        if url.endswith('.cast.gz'):
            tp = 'asciicast'
        elif url.endswith('.replay.mp4'):
            tp = 'mp4'
        elif (getattr(session.terminal, 'type', None) in all_guacamole_types) or \
                (session.protocol in ('rdp', 'vnc')):
            tp = 'guacamole'
        else:
            tp = 'json'

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

    def async_callback(self, *args, **kwargs):
        session_id = kwargs.get('pk')
        session = get_object_or_404(Session, id=session_id)
        detail = i18n_fmt(
            REPLAY_OP, self.request.user, _('View'), str(session)
        )
        self.record_logs(
            [session.asset_id], ActionChoices.download, detail,
            model=Session, resource_display=str(session)
        )

    def retrieve(self, request, *args, **kwargs):
        session_id = kwargs.get('pk')
        session = get_object_or_404(Session, id=session_id)

        storage = ReplayStorageHandler(session)
        local_path, url = storage.get_file_path_url()
        if local_path is None:
            # url => error message
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
