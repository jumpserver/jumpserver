# -*- coding: utf-8 -*-
#

from importlib import import_module

from django.conf import settings
from django.db.models import F, Value, CharField, Q
from django.db.models.functions import Cast
from django.http import HttpResponse, FileResponse
from django.utils.encoding import escape_uri_path
from rest_framework import generics
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.api import CommonApiMixin
from common.const.http import GET, POST
from common.drf.filters import DatetimeRangeFilterBackend
from common.permissions import IsServiceAccount
from common.plugins.es import QuerySet as ESQuerySet
from common.sessions.cache import user_session_manager
from common.storage.ftp_file import FTPFileStorageHandler
from common.utils import is_uuid, get_logger, lazyproperty
from orgs.mixins.api import OrgReadonlyModelViewSet, OrgModelViewSet
from orgs.models import Organization
from orgs.utils import current_org, tmp_to_root_org
from rbac.permissions import RBACPermission
from terminal.models import default_storage
from users.models import User
from .backends import TYPE_ENGINE_MAPPING
from .const import ActivityChoices
from .filters import UserSessionFilterSet, OperateLogFilterSet
from .models import (
    FTPLog, UserLoginLog, OperateLog, PasswordChangeLog,
    ActivityLog, JobLog, UserSession
)
from .serializers import (
    FTPLogSerializer, UserLoginLogSerializer, JobLogSerializer,
    OperateLogSerializer, OperateLogActionDetailSerializer,
    PasswordChangeLogSerializer, ActivityUnionLogSerializer,
    FileSerializer, UserSessionSerializer
)
from .utils import construct_userlogin_usernames

logger = get_logger(__name__)


class JobAuditViewSet(OrgReadonlyModelViewSet):
    model = JobLog
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    search_fields = ['creator__name', 'material']
    filterset_fields = ['creator__name', 'material']
    serializer_class = JobLogSerializer
    ordering = ['-date_start']


class FTPLogViewSet(OrgModelViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'asset', 'account', 'filename']
    search_fields = filterset_fields
    ordering = ['-date_start']
    http_method_names = ['post', 'get', 'head', 'options', 'patch']
    rbac_perms = {
        'download': 'audits.view_ftplog',
    }

    def get_storage(self):
        return FTPFileStorageHandler(self.get_object())

    @action(
        methods=[GET], detail=True, permission_classes=[RBACPermission, ],
        url_path='file/download'
    )
    def download(self, request, *args, **kwargs):
        ftp_log = self.get_object()
        ftp_storage = self.get_storage()
        local_path, url = ftp_storage.get_file_path_url()
        if local_path is None:
            # url => error message
            return HttpResponse(url)

        file = open(default_storage.path(local_path), 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        filename = escape_uri_path(ftp_log.filename)
        response["Content-Disposition"] = "attachment; filename*=UTF-8''{}".format(filename)
        return response

    @action(methods=[POST], detail=True, permission_classes=[IsServiceAccount, ], serializer_class=FileSerializer)
    def upload(self, request, *args, **kwargs):
        ftp_log = self.get_object()
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            name, err = ftp_log.save_file_to_storage(file)
            if not name:
                msg = "Failed save file `{}`: {}".format(ftp_log.id, err)
                logger.error(msg)
                return Response({'msg': str(err)}, status=400)
            url = default_storage.url(name)
            return Response({'url': url}, status=201)
        else:
            msg = 'Upload data invalid: {}'.format(serializer.errors)
            logger.error(msg)
            return Response({'msg': serializer.errors}, status=401)


class UserLoginCommonMixin:
    model = UserLoginLog
    serializer_class = UserLoginLogSerializer
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['id', 'username', 'ip', 'city', 'type', 'status', 'mfa']
    search_fields = ['id', 'username', 'ip', 'city']


class UserLoginLogViewSet(UserLoginCommonMixin, OrgReadonlyModelViewSet):
    @staticmethod
    def get_org_member_usernames():
        user_queryset = current_org.get_members()
        users = construct_userlogin_usernames(user_queryset)
        return users

    def get_queryset(self):
        queryset = super().get_queryset()
        if current_org.is_root():
            return queryset
        users = self.get_org_member_usernames()
        queryset = queryset.filter(username__in=users)
        return queryset


class MyLoginLogViewSet(UserLoginCommonMixin, OrgReadonlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(username=self.request.user.username)
        return qs


class ResourceActivityAPIView(generics.ListAPIView):
    serializer_class = ActivityUnionLogSerializer
    ordering_fields = ['datetime']
    rbac_perms = {
        'GET': 'audits.view_activitylog',
    }

    @staticmethod
    def get_operate_log_qs(fields, limit, org_q, resource_id=None):
        q, user = Q(resource_id=resource_id), None
        if is_uuid(resource_id):
            user = User.objects.filter(id=resource_id).first()
        if user is not None:
            q |= Q(user=str(user))
        queryset = OperateLog.objects.filter(q, org_q).annotate(
            r_type=Value(ActivityChoices.operate_log, CharField()),
            r_detail_id=Cast(F('id'), CharField()), r_detail=Value(None, CharField()),
            r_user=F('user'), r_action=F('action'),
        ).values(*fields)[:limit]
        return queryset

    @staticmethod
    def get_activity_log_qs(fields, limit, org_q, **filters):
        queryset = ActivityLog.objects.filter(org_q, **filters).annotate(
            r_type=F('type'), r_detail_id=F('detail_id'),
            r_detail=F('detail'), r_user=Value(None, CharField()),
            r_action=Value(None, CharField()),
        ).values(*fields)[:limit]
        return queryset

    def get_queryset(self):
        limit = 30
        resource_id = self.request.query_params.get('resource_id')
        fields = (
            'id', 'datetime', 'r_detail', 'r_detail_id',
            'r_user', 'r_action', 'r_type'
        )
        org_q = Q(org_id=Organization.SYSTEM_ID) | Q(org_id=current_org.id)
        if resource_id:
            org_q |= Q(org_id='') | Q(org_id=Organization.ROOT_ID)
        with tmp_to_root_org():
            qs1 = self.get_operate_log_qs(fields, limit, org_q, resource_id=resource_id)
            qs2 = self.get_activity_log_qs(fields, limit, org_q, resource_id=resource_id)
            queryset = qs2.union(qs1)
        return queryset.order_by('-datetime')[:limit]


class OperateLogViewSet(OrgReadonlyModelViewSet):
    model = OperateLog
    serializer_class = OperateLogSerializer
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_class = OperateLogFilterSet
    search_fields = ['resource', 'user']
    ordering = ['-datetime']

    @lazyproperty
    def is_action_detail(self):
        return self.detail and self.request.query_params.get('type') == 'action_detail'

    def get_serializer_class(self):
        if self.is_action_detail:
            return OperateLogActionDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        qs = OperateLog.objects.all()
        if self.is_action_detail:
            with tmp_to_root_org():
                qs |= OperateLog.objects.filter(org_id=Organization.SYSTEM_ID)
        es_config = settings.OPERATE_LOG_ELASTICSEARCH_CONFIG
        if es_config:
            engine_mod = import_module(TYPE_ENGINE_MAPPING['es'])
            store = engine_mod.OperateLogStore(es_config)
            if store.ping(timeout=2):
                qs = ESQuerySet(store)
                qs.model = OperateLog
        return qs


class PasswordChangeLogViewSet(OrgReadonlyModelViewSet):
    model = PasswordChangeLog
    serializer_class = PasswordChangeLogSerializer
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_fields = ['user', 'change_by', 'remote_addr']
    search_fields = filterset_fields
    ordering = ['-datetime']

    def get_queryset(self):
        queryset = super().get_queryset()
        if not current_org.is_root():
            users = current_org.get_members()
            queryset = queryset.filter(
                user__in=[str(user) for user in users]
            )
        return queryset


class UserSessionViewSet(CommonApiMixin, viewsets.ModelViewSet):
    http_method_names = ('get', 'post', 'head', 'options', 'trace')
    serializer_class = UserSessionSerializer
    filterset_class = UserSessionFilterSet
    search_fields = ['id', 'ip', 'city']
    rbac_perms = {
        'offline': ['audits.offline_usersession']
    }

    @property
    def org_user_ids(self):
        user_ids = current_org.get_members().values_list('id', flat=True)
        return user_ids

    def get_queryset(self):
        keys = UserSession.get_keys()
        queryset = UserSession.objects.filter(key__in=keys)
        if current_org.is_root():
            return queryset
        user_ids = self.org_user_ids
        queryset = queryset.filter(user_id__in=user_ids)
        return queryset

    @action(['POST'], detail=False, url_path='offline')
    def offline(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        queryset = self.get_queryset()
        session_key = request.session.session_key
        queryset = queryset.exclude(key=session_key).filter(id__in=ids)
        if not queryset.exists():
            return Response(status=status.HTTP_200_OK)

        keys = queryset.values_list('key', flat=True)
        for key in keys:
            user_session_manager.decrement_or_remove(key)
        queryset.delete()
        return Response(status=status.HTTP_200_OK)
