# -*- coding: utf-8 -*-
#
import os

from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.utils.encoding import escape_uri_path
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin
from django.db.models import F, Value
from django.db.models.functions import Concat
from rest_framework.response import Response

from common.const.http import GET
from common.drf.renders import PassthroughRenderer
from common.mixins import AsyncApiMixin
from common.permissions import IsOrgAdminOrAppUser, IsOrgAuditor, IsOrgAdmin
from common.drf.filters import DatetimeRangeFilter
from common.api import CommonGenericViewSet
from common.utils import get_logger
from orgs.mixins.api import OrgGenericViewSet, OrgBulkModelViewSet, OrgRelationMixin
from orgs.utils import current_org
from ops.models import CommandExecution
from terminal.models import default_storage
from .models import FTPLog, UserLoginLog, OperateLog, PasswordChangeLog
from .serializers import FTPLogSerializer, UserLoginLogSerializer, CommandExecutionSerializer, FileSerializer
from .serializers import OperateLogSerializer, PasswordChangeLogSerializer, CommandExecutionHostsRelationSerializer
from .utils import get_ftplog_file_url

logger = get_logger(__name__)


class FTPLogViewSet(CreateModelMixin,
                    UpdateModelMixin,
                    ListModelMixin,
                    OrgGenericViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor,)
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'asset', 'system_user', 'filename']
    search_fields = filterset_fields
    ordering = ['-date_start']

    def is_need_async(self):
        if self.action != 'retrieve':
            return False
        return True

    @action(methods=[GET], detail=True, renderer_classes=(PassthroughRenderer,), url_path='file/download', url_name='ftp-file-download')
    def download_ftp_file(self, request, *args, **kwargs):
        ftp_log = self.get_object()

        local_path, url = get_ftplog_file_url(ftp_log, str(ftp_log.id))
        if local_path is None:
            error = url
            return HttpResponse(error)
        file = open(default_storage.path(local_path), 'rb')

        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        # 这里要注意哦，网上查到的方法都是response['Content-Disposition']='attachment;filename="filename.py"',
        # 但是如果文件名是英文名没问题，如果文件名包含中文，下载下来的文件名会被改为url中的path。
        filename = escape_uri_path(ftp_log.filename)
        filename = os.path.split(filename)[-1]
        disposition = "attachment; filename*=UTF-8''{}".format(filename)
        response["Content-Disposition"] = disposition
        return response


class FTPLogFileViewSet(AsyncApiMixin, viewsets.ViewSet):
    serializer_class = FileSerializer
    permission_classes = (IsOrgAdminOrAppUser | IsOrgAuditor,)
    ftp_log = None
    download_cache_key = "FTP_LOG_FILE_DOWNLOAD_{}"

    def create(self, request, *args, **kwargs):
        ftp_log_id = kwargs.get('pk')
        ftp_log = get_object_or_404(FTPLog, id=ftp_log_id)
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']
            name, err = ftp_log.save_file_to_storage(file)
            if not name:
                msg = "Failed save file `{}`: {}".format(ftp_log_id, err)
                logger.error(msg)
                return Response({'msg': str(err)}, status=400)
            FTPLog.objects.filter(id=ftp_log_id).update(has_file_record=True)
            url = default_storage.url(name)
            return Response({'url': url}, status=201)
        else:
            msg = 'Upload data invalid: {}'.format(serializer.errors)
            logger.error(msg)
            return Response({'msg': serializer.errors}, status=401)

    def is_need_async(self):
        return False


class UserLoginLogViewSet(ListModelMixin, CommonGenericViewSet):
    queryset = UserLoginLog.objects.all()
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    serializer_class = UserLoginLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['username', 'ip', 'city', 'type', 'status', 'mfa']
    search_fields =['username', 'ip', 'city']

    @staticmethod
    def get_org_members():
        users = current_org.get_members().values_list('username', flat=True)
        return users

    def get_queryset(self):
        queryset = super().get_queryset()
        if not current_org.is_default():
            users = self.get_org_members()
            queryset = queryset.filter(username__in=users)
        return queryset


class OperateLogViewSet(ListModelMixin, OrgGenericViewSet):
    model = OperateLog
    serializer_class = OperateLogSerializer
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'action', 'resource_type', 'resource', 'remote_addr']
    search_fields = ['resource']
    ordering = ['-datetime']


class PasswordChangeLogViewSet(ListModelMixin, CommonGenericViewSet):
    queryset = PasswordChangeLog.objects.all()
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    serializer_class = PasswordChangeLogSerializer
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'change_by', 'remote_addr']
    ordering = ['-datetime']

    def get_queryset(self):
        users = current_org.get_members()
        queryset = super().get_queryset().filter(
            user__in=[user.__str__() for user in users]
        )
        return queryset


class CommandExecutionViewSet(ListModelMixin, OrgGenericViewSet):
    model = CommandExecution
    serializer_class = CommandExecutionSerializer
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    extra_filter_backends = [DatetimeRangeFilter]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user__name', 'command', 'run_as__name', 'is_finished']
    search_fields = ['command', 'user__name', 'run_as__name']
    ordering = ['-date_created']

    def get_queryset(self):
        queryset = super().get_queryset()
        if current_org.is_root():
            return queryset
        queryset = queryset.filter(run_as__org_id=current_org.org_id())
        return queryset


class CommandExecutionHostRelationViewSet(OrgRelationMixin, OrgBulkModelViewSet):
    serializer_class = CommandExecutionHostsRelationSerializer
    m2m_field = CommandExecution.hosts.field
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    filterset_fields = [
        'id', 'asset', 'commandexecution'
    ]
    search_fields = ('asset__hostname', )
    http_method_names = ['options', 'get']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(
            asset_display=Concat(
                F('asset__hostname'), Value('('),
                F('asset__ip'), Value(')')
            )
        )
        return queryset
