# -*- coding: utf-8 -*-
#
from importlib import import_module
from datetime import datetime, timedelta, timezone as datetime_timezone

from django.conf import settings
from django.db.models import F, Value, CharField, Q, BooleanField, Case, DateTimeField, Exists, OuterRef, When
from django.db.models.functions import Cast, Coalesce
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.encoding import escape_uri_path
from django_celery_beat.models import PeriodicTask
from rest_framework import generics
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from jumpserver.rewriting.pagination import MaxLimitOffsetPagination

from common.api import CommonApiMixin, ReportExportMixin
from common.const.http import GET, POST
from common.drf.filters import DatetimeRangeFilterBackend
from common.drf.throttling import FileTransferThrottle
from common.permissions import IsServiceAccount
from common.plugins.es import QuerySet as ESQuerySet
from common.sessions.cache import user_session_manager
from common.storage.ftp_file import FTPFileStorageHandler
from common.utils import is_uuid, get_logger, lazyproperty
from ops.const import Types
from ops.models import Job
from orgs.mixins.api import OrgReadonlyModelViewSet, OrgModelViewSet
from orgs.models import Organization
from orgs.utils import current_org, tmp_to_root_org
from rbac.permissions import RBACPermission
from terminal.models import default_storage
from tickets.filters import TicketFilter
from tickets.reporting import TicketReportExporter
from tickets.serializers.ticket import TicketSerializer
from users.models import User
from .backends import TYPE_ENGINE_MAPPING
from .const import ActivityChoices, ActionChoices
from .filters import (
    FTPLogFilterSet, JobLogFilterSet, OperateLogFilterSet,
    JobsAuditFilterSet,
    PasswordChangeLogFilterSet,
    UserLoginLogFilterSet, UserSessionFilterSet, ClientUserSessionFilterSet,
)
from .models import (
    FTPLog, UserLoginLog, OperateLog, PasswordChangeLog,
    ActivityLog, JobLog, TicketAudit, UserSession, IntegrationApplicationLog
)
from .reporting import (
    FTPLogReportExporter, UserLoginLogReportExporter, PasswordChangeLogReportExporter,
    OperateLogReportExporter, JobsAuditReportExporter,
    JobLogAuditReportExporter,
)
from .serializers import (
    FTPLogSerializer, UserLoginLogSerializer, JobLogSerializer,
    OperateLogSerializer, OperateLogActionDetailSerializer,
    PasswordChangeLogSerializer, ActivityUnionLogSerializer,
    FileSerializer, UserSessionSerializer, JobsAuditSerializer,
    OperateLogFullSerializer, ServiceAccessLogSerializer
)
from .utils import construct_userlogin_usernames, record_operate_log_and_activity_log

logger = get_logger(__name__)


class ServiceAccessLogViewSet(OrgReadonlyModelViewSet):
    model = IntegrationApplicationLog
    serializer_class = ServiceAccessLogSerializer
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [('datetime', ('date_from', 'date_to'))]
    filterset_fields = [
        'id', 'service', 'service_id', 'asset', 'asset_id', 'account', 'account_id',
        'remote_addr', 'instance_id', 'source', 'result', 'credential_id',
        'credential_key', 'revision', 'summary',
    ]
    search_fields = ['id', 'service', 'service_id', 'asset', 'account', 'instance_id',
                     'remote_addr', 'credential_key', 'summary']
    ordering_fields = ['datetime']
    ordering = ['-datetime', '-id']

    def get_queryset(self):
        from accounts.models import IntegrationApplication
        queryset = super().get_queryset()
        if not current_org.is_root():
            application_ids = IntegrationApplication.objects.filter(org_id=str(current_org.id)).values('id')
            queryset = queryset.filter(
                Q(org_id=str(current_org.id)) | Q(org_id='', service_id__in=application_ids)
            )
        return queryset


class JobLogAuditViewSet(ReportExportMixin, OrgReadonlyModelViewSet):
    model = JobLog
    filterset_class = JobLogFilterSet
    report_exporter_class = JobLogAuditReportExporter
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    search_fields = ['creator__name', 'material']
    serializer_class = JobLogSerializer
    ordering_fields = [
        'material', 'job_type', 'date_start', 'date_finished',
    ]
    ordering = ['-date_start']


class JobsAuditViewSet(ReportExportMixin, OrgModelViewSet):
    model = Job
    search_fields = ['creator__name', 'args', 'name']
    filterset_class = JobsAuditFilterSet
    serializer_class = JobsAuditSerializer
    report_exporter_class = JobsAuditReportExporter
    ordering_fields = [
        'name', 'args', 'type', 'crontab', 'interval', 'created_by',
        'is_periodic',
    ]
    ordering = ['-is_periodic', '-date_updated']
    http_method_names = ['get', 'options', 'patch']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.exclude(type=Types.upload_file).filter(instant=False)
        return queryset

    def perform_update(self, serializer):
        job = self.get_object()
        is_periodic = serializer.validated_data.get('is_periodic')
        if job.is_periodic != is_periodic:
            job.is_periodic = is_periodic
            job.save()
        name, task, args, kwargs = job.get_register_task()
        task_obj = PeriodicTask.objects.filter(name=name).first()
        if task_obj:
            is_periodic = job.is_periodic
            if task_obj.enabled != is_periodic:
                task_obj.enabled = is_periodic
                task_obj.save()
        return super().perform_update(serializer)


class FTPLogViewSet(ReportExportMixin, OrgModelViewSet):
    model = FTPLog
    serializer_class = FTPLogSerializer
    report_exporter_class = FTPLogReportExporter
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('date_start', ('date_from', 'date_to'))
    ]
    filterset_class = FTPLogFilterSet
    search_fields = [
        'id', 'user', 'asset', 'account', 'filename', 'remote_addr',
        'session',
    ]
    ordering = ['-date_start']
    http_method_names = ['post', 'get', 'head', 'options', 'patch']
    rbac_perms = {
        'download': 'audits.view_ftplog',
    }

    def get_storage(self):
        return FTPFileStorageHandler(self.get_object())

    @action(
        methods=[GET], detail=True, permission_classes=[RBACPermission, ],
        throttle_classes=[FileTransferThrottle],
        url_path='file/download'
    )
    def download(self, request, *args, **kwargs):
        ftp_log = self.get_object()
        ftp_storage = self.get_storage()
        local_path, url = ftp_storage.get_file_path_url()
        if local_path is None:
            logger.warning('FTP file unavailable for log %s: %s', ftp_log.id, url)
            return JsonResponse({
                'detail': gettext('File not found'),
                'code': 'file_not_found',
            }, status=status.HTTP_404_NOT_FOUND)

        file = open(default_storage.path(local_path), 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        filename = escape_uri_path(ftp_log.filename)
        response["Content-Disposition"] = "attachment; filename*=UTF-8''{}".format(filename)

        record_operate_log_and_activity_log(
            [ftp_log.id], ActionChoices.download, '', self.model,
            resource_display=f'{ftp_log.asset}: {ftp_log.filename}',
        )
        return response

    @action(methods=[POST], detail=True, permission_classes=[IsServiceAccount, ],
            throttle_classes=[FileTransferThrottle],
            serializer_class=FileSerializer)
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


class UserLoginCommonMixin(ReportExportMixin):
    model = UserLoginLog
    serializer_class = UserLoginLogSerializer
    report_exporter_class = UserLoginLogReportExporter
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_class = UserLoginLogFilterSet
    search_fields = [
        'id', 'username', 'ip', 'city', 'user_agent',
    ]


class UserLoginLogViewSet(UserLoginCommonMixin, OrgReadonlyModelViewSet):
    @staticmethod
    def get_org_member_usernames():
        user_queryset = current_org.get_members()
        users = construct_userlogin_usernames(user_queryset)
        return users

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.model.filter_queryset_by_org(queryset)
        return queryset


class MyLoginLogViewSet(UserLoginCommonMixin, OrgReadonlyModelViewSet):
    chat_ai_required_permissions = ()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        username = self.request.user.username
        q = Q(username=username) | Q(username__icontains=f'({username})')
        qs = qs.filter(q)
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
            r_type=F('type'), r_detail_id=Cast(F('detail_id'), CharField()),
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

        org_q = Q()
        if not current_org.is_root():
            org_q = Q(org_id=Organization.SYSTEM_ID) | Q(org_id=current_org.id)
            if resource_id:
                org_q |= Q(org_id='') | Q(org_id=Organization.ROOT_ID)

        with tmp_to_root_org():
            qs1 = self.get_operate_log_qs(fields, limit, org_q, resource_id=resource_id)
            qs2 = self.get_activity_log_qs(fields, limit, org_q, resource_id=resource_id)
            queryset = qs2.union(qs1)
        return queryset.order_by('-datetime')[:limit]


class OperateLogViewSet(ReportExportMixin, OrgReadonlyModelViewSet):
    model = OperateLog
    serializer_class = OperateLogSerializer
    report_exporter_class = OperateLogReportExporter
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
        elif self.request.query_params.get('format'):
            return OperateLogFullSerializer
        return OperateLogSerializer

    def get_queryset(self):
        current_org_id = str(current_org.id)

        with tmp_to_root_org():
            qs = OperateLog.objects.all()
            if current_org_id != Organization.ROOT_ID:
                filtered_org_ids = {current_org_id}
                if current_org_id == Organization.DEFAULT_ID:
                    filtered_org_ids.update(Organization.INTERNAL_IDS)
                if self.is_action_detail:
                    filtered_org_ids.add(Organization.SYSTEM_ID)
                qs = OperateLog.objects.filter(org_id__in=filtered_org_ids)

        es_config = settings.OPERATE_LOG_ELASTICSEARCH_CONFIG
        if es_config:
            engine_mod = import_module(TYPE_ENGINE_MAPPING['es'])
            store = engine_mod.OperateLogStore(es_config)
            if store.ping(timeout=2):
                qs = ESQuerySet(store)
                qs.model = OperateLog
        return qs


class PasswordChangeLogViewSet(ReportExportMixin, OrgReadonlyModelViewSet):
    chat_ai_safe_sensitive_actions = ('list', 'retrieve')
    model = PasswordChangeLog
    serializer_class = PasswordChangeLogSerializer
    report_exporter_class = PasswordChangeLogReportExporter
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('datetime', ('date_from', 'date_to'))
    ]
    filterset_class = PasswordChangeLogFilterSet
    search_fields = ['id', 'user', 'change_by', 'remote_addr']
    ordering = ['-datetime']

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.model.filter_queryset_by_org(queryset)


class TicketAuditViewSet(ReportExportMixin, OrgReadonlyModelViewSet):
    model = TicketAudit
    report_exporter_class = TicketReportExporter
    serializer_class = TicketSerializer
    filterset_class = TicketFilter
    extra_filter_backends = [DatetimeRangeFilterBackend]
    date_range_filter_fields = [
        ('date_created', ('date_from', 'date_to'))
    ]
    search_fields = ['title', 'type', 'status']
    ordering_fields = [
        'title', 'serial_num', 'type', 'state', 'status', 'applicant',
        'date_created',
    ]
    ordering = ('-date_created',)
    permission_classes = [RBACPermission]

    def get_queryset(self):
        queryset = self.model.objects.all()
        if not current_org.is_root():
            queryset = queryset.filter(org_id=str(current_org.id))
        return queryset


class UserDevicePagination(MaxLimitOffsetPagination):
    def get_count(self, queryset):
        # Preserve both projections when counting the SQL union.
        return queryset.count()


class UserSessionViewSet(CommonApiMixin, viewsets.ModelViewSet):
    http_method_names = ('get', 'post', 'head', 'options', 'trace')
    serializer_class = UserSessionSerializer
    pagination_class = UserDevicePagination
    page_no_limit = True  # Apply the unpaged cap after merging both sources.
    ordering_fields = ('id', 'date_created', 'ip', 'type', 'backend', 'is_active')
    device_fields = (
        'id', 'user_id', 'ip', 'city', 'user_agent', 'type', 'backend',
        'date_created', 'is_active', 'date_expired', 'is_locked', 'key',
        'policy_expires_at',
    )
    filterset_class = UserSessionFilterSet
    search_fields = [
        'id', 'user__name', 'user__username', 'ip', 'city',
        'backend', 'user_agent',
    ]
    rbac_perms = {
        'offline': ['audits.offline_usersession']
    }

    @property
    def org_user_ids(self):
        user_ids = current_org.get_members().values_list('id', flat=True)
        return user_ids

    def get_queryset(self):
        keys = user_session_manager.get_keys()
        queryset = UserSession.objects.filter(key__in=keys)
        if current_org.is_root():
            return queryset
        user_ids = self.org_user_ids
        queryset = queryset.filter(user_id__in=user_ids)
        return queryset

    def get_client_queryset(self):
        from authentication.models import ClientLoginSession
        from authentication.services.client_login_session import client_applications
        from oauth2_provider.models import get_refresh_token_model

        now = timezone.now()
        live_refresh = get_refresh_token_model().objects.filter(
            application_id=OuterRef('application_id'), token_family=OuterRef('token_family'),
            revoked__isnull=True, access_token__isnull=False,
        )
        queryset = ClientLoginSession.objects.filter(
            application__in=client_applications(), revoked_at__isnull=True,
        ).annotate(
            date_created=F('authenticated_at'), date_expired=Coalesce('policy_expires_at', 'expires_at'),
            has_live_refresh=Exists(live_refresh),
            # Existing token last-used writes are batched for up to a minute.
            # Three minutes covers that delay and the client's one-minute sync.
            is_active=Exists(live_refresh.filter(access_token__updated__gte=now - timedelta(minutes=3))),
            city=Value('', CharField()), type=Value('C', CharField()),
            backend=Value('OAuth2', CharField()), key=Value('', CharField()),
        ).filter(has_live_refresh=True).filter(Q(date_expired__isnull=True) | Q(date_expired__gt=now))
        if not current_org.is_root():
            queryset = queryset.filter(user_id__in=self.org_user_ids)
        return queryset

    def device_rows(self, rows):
        if not rows:
            return rows
        from authentication.services.client_login_session import client_login_policy
        from authentication.services.idle_lock import (
            IDLE_LOCK_CATEGORY, PERSONAL_SETTINGS, effective_idle_lock_time,
            idle_lock_limits, personal_client_login_policy,
        )
        from common.sessions import policy_locked, policy_expiry, session_login_policies
        from users.models import Preference
        from .models import _get_city_display

        users = User.objects.in_bulk({row['user_id'] for row in rows})
        preferences = {user_id: {} for user_id in users}
        for user_id, name, value in Preference.objects.filter(
            user_id__in=users, category=IDLE_LOCK_CATEGORY, name__in=PERSONAL_SETTINGS,
        ).values_list('user_id', 'name', 'value'):
            preferences[user_id][name] = value
        web_policies = session_login_policies([row['key'] for row in rows if row['type'] != 'C'])
        web_idle_limit = idle_lock_limits(use_cache=True)['web_idle_lock_time']
        client_policy = client_login_policy() if any(row['type'] == 'C' for row in rows) else None
        for row in rows:
            row['user'] = users[row['user_id']]
            row['city_display'] = _get_city_display(row['ip'], row['city'])
            row['backend_display'] = gettext(row['backend'])
            personal = preferences[row['user_id']]
            if row['type'] == 'C':
                policy = personal_client_login_policy(row['user_id'], client_policy, preferences=personal)
                grace = row['policy_expires_at']
                row['session_policy'] = {
                    'duration': policy['max_session_time'] * 60, 'renew': False,
                    'reauth_on_exit': policy['reauth_on_exit'], 'idle_lock_time': policy['idle_lock_time'],
                    'grace_expires_at': grace.isoformat() if grace else None,
                }
            else:
                policy = web_policies.get(row['key'])
                row['is_active'] = bool(policy)
                row['is_locked'] = policy_locked(policy)
                row['date_expired'] = (
                    datetime.fromtimestamp(policy_expiry(policy),
                                           tz=datetime_timezone.utc) if policy
                    else None
                )
                row['session_policy'] = {
                    'duration': policy['duration'], 'renew': policy['renew'],
                    'reauth_on_exit': policy['browser_close'],
                    'idle_lock_time': effective_idle_lock_time(
                        web_idle_limit, int(personal['web_idle_lock_time']) if 'web_idle_lock_time' in personal else None,
                    ), 'grace_expires_at': None,
                } if policy else None
        return rows

    def list(self, request, *args, **kwargs):
        active_keys = user_session_manager.get_active_keys()
        web = self.filter_queryset(self.get_queryset().annotate(
            is_active=Case(When(key__in=active_keys, then=True), default=False, output_field=BooleanField()),
            # Keep the union projection aligned; Web lock state comes from Session below.
            is_locked=Value(False, BooleanField()),
            date_expired=Value(None, DateTimeField()),
            policy_expires_at=Value(None, DateTimeField()),
        ))
        original_filterset = self.filterset_class
        self.filterset_class = ClientUserSessionFilterSet
        try:
            client = self.filter_queryset(self.get_client_queryset())
        finally:
            self.filterset_class = original_filterset
        ordering = web.query.order_by or ('-date_created',)
        queryset = web.order_by().values(*self.device_fields).union(
            client.order_by().values(*self.device_fields), all=True,
        ).order_by(*ordering, 'id')
        # Union rows must not be reloaded as Web-only UserSession objects.
        queryset.custom = True
        page = self.paginate_queryset(queryset)
        if page is None and settings.DEFAULT_PAGE_SIZE:
            queryset = queryset[:settings.DEFAULT_PAGE_SIZE]
        rows = self.device_rows(list(page if page is not None else queryset))
        data = self.get_serializer(rows, many=True).data
        return self.get_paginated_response(data) if page is not None else Response(data)

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get(self.lookup_field)
        if not is_uuid(pk):
            raise Http404
        instance = self.get_queryset().filter(pk=pk).first()
        if instance is not None:
            self.check_object_permissions(request, instance)
            row = {field: getattr(instance, field, None) for field in self.device_fields}
            return Response(self.get_serializer(self.device_rows([row])[0]).data)
        row = self.get_client_queryset().filter(pk=pk).values(*self.device_fields).first()
        if row is None:
            raise Http404
        self.check_object_permissions(request, row)
        return Response(self.get_serializer(self.device_rows([row])[0]).data)

    @action(['POST'], detail=False, url_path='offline')
    def offline(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        if not isinstance(ids, list) or not all(isinstance(pk, str) and is_uuid(pk) for pk in ids):
            raise ValidationError({'ids': 'Expected a list of session UUIDs.'})
        queryset = self.get_queryset()
        session_key = request.session.session_key
        queryset = queryset.exclude(key=session_key).filter(id__in=ids)
        keys = queryset.values_list('key', flat=True)
        for key in keys:
            user_session_manager.remove(key)
        queryset.delete()

        from authentication.services.client_login_session import revoke_session
        clients = self.get_client_queryset().filter(pk__in=ids)
        current_client = getattr(request, 'client_login_session', None)
        if current_client is not None:
            clients = clients.exclude(pk=current_client.pk)
        for client in clients:
            revoke_session(client, 'security_revoke')
        return Response(status=status.HTTP_200_OK)
