import time
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count, Max, F, CharField
from django.db.models.functions import Cast
from django.http.response import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.timesince import timesince
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.const import AllTypes
from assets.models import Asset
from audits.api import OperateLogViewSet
from audits.const import LoginStatusChoices
from audits.models import UserLoginLog, PasswordChangeLog, OperateLog, FTPLog, JobLog
from audits.utils import construct_userlogin_usernames
from common.utils import lazyproperty
from common.utils.timezone import local_now, local_zero_hour
from ops.const import JobStatus
from orgs.caches import OrgResourceStatisticsCache
from orgs.utils import current_org
from terminal.const import RiskLevelChoices
from terminal.models import Session, Command
from terminal.utils import ComponentsPrometheusMetricsUtil
from users.models import User

__all__ = ['IndexApi']


class DateTimeMixin:
    request: Request

    @property
    def org(self):
        return current_org

    @lazyproperty
    def days(self):
        query_params = self.request.query_params
        count = query_params.get('days')
        count = int(count) if count else 1
        return count

    @property
    def days_to_datetime(self):
        days = self.days
        if days == 1:
            t = local_zero_hour()
        else:
            t = local_now() - timezone.timedelta(days=days)
        return t

    @lazyproperty
    def date_start_end(self):
        return self.days_to_datetime.date(), local_now().date() + timezone.timedelta(days=1)

    @lazyproperty
    def dates_list(self):
        return [
            (local_now() - timezone.timedelta(days=i)).date()
            for i in range(self.days - 1, -1, -1)
        ]

    def get_dates_metrics_date(self):
        return [d.strftime('%m-%d') for d in self.dates_list] or ['0']

    def get_logs_queryset_filter(self, qs, query_field, is_timestamp=False):
        dt = self.days_to_datetime
        t = dt.timestamp() if is_timestamp else dt
        query = {f'{query_field}__gte': t}
        return qs.filter(**query)

    def get_logs_queryset(self, queryset, query_params):
        query = {}
        users = self.org.get_members()
        if not self.org.is_root():
            if query_params == 'username':
                query = {
                    f'{query_params}__in': construct_userlogin_usernames(users)
                }
            else:
                query = {
                    f'{query_params}__in': [str(user) for user in users]
                }
        queryset = queryset.filter(**query)
        return queryset

    @lazyproperty
    def sessions_queryset(self):
        return self.get_logs_queryset_filter(Session.objects, 'date_start')

    @lazyproperty
    def login_logs_queryset(self):
        qs = UserLoginLog.objects.all()
        qs = self.get_logs_queryset_filter(qs, 'datetime')
        queryset = self.get_logs_queryset(qs, 'username')
        return queryset

    @lazyproperty
    def password_change_logs_queryset(self):
        qs = PasswordChangeLog.objects.all()
        qs = self.get_logs_queryset_filter(qs, 'datetime')
        queryset = self.get_logs_queryset(qs, 'user')
        return queryset

    @lazyproperty
    def operate_logs_queryset(self):
        qs = OperateLogViewSet().get_queryset()
        return self.get_logs_queryset_filter(qs, 'datetime')

    @lazyproperty
    def ftp_logs_queryset(self):
        qs = FTPLog.objects.all()
        return self.get_logs_queryset_filter(qs, 'date_start')

    @lazyproperty
    def command_queryset(self):
        qs = Command.objects.all()
        return self.get_logs_queryset_filter(qs, 'timestamp', is_timestamp=True)

    @lazyproperty
    def job_logs_queryset(self):
        qs = JobLog.objects.all()
        return self.get_logs_queryset_filter(qs, 'date_start')


class DatesLoginMetricMixin:
    dates_list: list
    date_start_end: tuple
    command_queryset: Command.objects
    sessions_queryset: Session.objects
    ftp_logs_queryset: FTPLog.objects
    job_logs_queryset: JobLog.objects
    login_logs_queryset: UserLoginLog.objects
    operate_logs_queryset: OperateLog.objects
    password_change_logs_queryset: PasswordChangeLog.objects

    @lazyproperty
    def get_type_to_assets(self):
        result = Asset.objects.annotate(type=F('platform__type')). \
            values('type').order_by('type').annotate(total=Count(1))
        all_types_dict = dict(AllTypes.choices())
        result = list(result)
        for i in result:
            tp = i['type']
            i['label'] = all_types_dict.get(tp, tp)
        return result

    def filter_date_start_end(self, queryset, field_name):
        query = {f'{field_name}__range': self.date_start_end}
        return queryset.filter(**query)

    def get_date_metrics(self, queryset, field_name, count_field):
        queryset = self.filter_date_start_end(queryset, field_name)
        queryset = queryset.values_list(field_name, count_field)

        date_group_map = defaultdict(set)
        for datetime, count_field in queryset:
            date_str = str(datetime.date())
            date_group_map[date_str].add(count_field)

        return [
            len(date_group_map.get(str(d), set()))
            for d in self.dates_list
        ]

    def get_dates_metrics_total_count_login(self):
        return self.get_date_metrics(UserLoginLog.objects, 'datetime', 'id')

    def get_dates_metrics_total_count_active_users(self):
        return self.get_date_metrics(Session.objects, 'date_start', 'user_id')

    def get_dates_metrics_total_count_active_assets(self):
        return self.get_date_metrics(Session.objects, 'date_start', 'asset_id')

    def get_dates_metrics_total_count_sessions(self):
        return self.get_date_metrics(Session.objects, 'date_start', 'id')

    def get_dates_login_times_assets(self):
        assets = self.sessions_queryset.values("asset") \
            .annotate(total=Count("asset")) \
            .annotate(last=Cast(Max("date_start"), output_field=CharField())) \
            .order_by("-total")
        return list(assets[:10])

    def get_dates_login_times_users(self):
        users = self.sessions_queryset.values("user_id") \
            .annotate(total=Count("user_id")) \
            .annotate(user=Max('user')) \
            .annotate(last=Cast(Max("date_start"), output_field=CharField())) \
            .order_by("-total")
        return list(users[:10])

    def get_dates_login_record_sessions(self):
        sessions = self.sessions_queryset.order_by('-date_start')
        sessions = [
            {
                'user': session.user,
                'asset': session.asset,
                'is_finished': session.is_finished,
                'date_start': str(session.date_start),
                'timesince': timesince(session.date_start)
            }
            for session in sessions[:10]
        ]
        return sessions

    @lazyproperty
    def user_login_logs_amount(self):
        return self.login_logs_queryset.count()

    @lazyproperty
    def user_login_success_logs_amount(self):
        return self.login_logs_queryset.filter(status=LoginStatusChoices.success).count()

    @lazyproperty
    def user_login_amount(self):
        return self.login_logs_queryset.values('username').distinct().count()

    @lazyproperty
    def operate_logs_amount(self):
        return self.operate_logs_queryset.count()

    @lazyproperty
    def change_password_logs_amount(self):
        return self.password_change_logs_queryset.count()

    @lazyproperty
    def commands_amount(self):
        return self.command_queryset.count()

    @lazyproperty
    def commands_danger_amount(self):
        return self.command_queryset.filter(risk_level=RiskLevelChoices.reject).count()

    @lazyproperty
    def job_logs_running_amount(self):
        return self.job_logs_queryset.filter(status=JobStatus.running).count()

    @lazyproperty
    def job_logs_failed_amount(self):
        return self.job_logs_queryset.filter(
            status__in=[JobStatus.failed, JobStatus.timeout]
        ).count()

    @lazyproperty
    def job_logs_amount(self):
        return self.job_logs_queryset.count()

    @lazyproperty
    def sessions_amount(self):
        return self.sessions_queryset.count()

    @lazyproperty
    def online_sessions_amount(self):
        return self.sessions_queryset.filter(is_finished=False).count()

    @lazyproperty
    def ftp_logs_amount(self):
        return self.ftp_logs_queryset.count()


class IndexApi(DateTimeMixin, DatesLoginMetricMixin, APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': ['rbac.view_audit | rbac.view_console'],
    }

    def get(self, request, *args, **kwargs):
        data = {}

        query_params = self.request.query_params

        caches = OrgResourceStatisticsCache(self.org)

        _all = query_params.get('all')

        if _all or query_params.get('total_count') or query_params.get('total_count_users'):
            data.update({
                'total_count_users': caches.users_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_assets'):
            data.update({
                'total_count_assets': caches.assets_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_users_this_week'):
            data.update({
                'total_count_users_this_week': caches.new_users_amount_this_week,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_assets_this_week'):
            data.update({
                'total_count_assets_this_week': caches.new_assets_amount_this_week,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_login_users'):
            data.update({
                'total_count_login_users': self.user_login_amount
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_today_active_assets'):
            data.update({
                'total_count_today_active_assets': caches.total_count_today_active_assets,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_online_users'):
            data.update({
                'total_count_online_users': caches.total_count_online_users,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_online_sessions'):
            data.update({
                'total_count_online_sessions': caches.total_count_online_sessions,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_today_failed_sessions'):
            data.update({
                'total_count_today_failed_sessions': caches.total_count_today_failed_sessions,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_user_login_logs'):
            data.update({
                'total_count_user_login_logs': self.user_login_logs_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_user_login_success_logs'):
            data.update({
                'total_count_user_login_success_logs': self.user_login_success_logs_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_operate_logs'):
            data.update({
                'total_count_operate_logs': self.operate_logs_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_change_password_logs'):
            data.update({
                'total_count_change_password_logs': self.change_password_logs_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_commands'):
            data.update({
                'total_count_commands': self.commands_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_commands_danger'):
            data.update({
                'total_count_commands_danger': self.commands_danger_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_history_sessions'):
            data.update({
                'total_count_history_sessions': self.sessions_amount - self.online_sessions_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_ftp_logs'):
            data.update({
                'total_count_ftp_logs': self.ftp_logs_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_job_logs'):
            data.update({
                'total_count_job_logs': self.job_logs_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_job_logs_running'):
            data.update({
                'total_count_job_logs_running': self.job_logs_running_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_job_logs_failed'):
            data.update({
                'total_count_job_logs_failed': self.job_logs_failed_amount,
            })

        if _all or query_params.get('total_count') or query_params.get('total_count_type_to_assets_amount'):
            data.update({
                'total_count_type_to_assets_amount': self.get_type_to_assets,
            })

        if _all or query_params.get('session_dates_metrics'):
            data.update({
                'dates_metrics_date': self.get_dates_metrics_date(),
                'dates_metrics_total_count_session': self.get_dates_metrics_total_count_sessions(),
            })

        if _all or query_params.get('dates_metrics'):
            data.update({
                'dates_metrics_date': self.get_dates_metrics_date(),
                'dates_metrics_total_count_login': self.get_dates_metrics_total_count_login(),
                'dates_metrics_total_count_active_users': self.get_dates_metrics_total_count_active_users(),
                'dates_metrics_total_count_active_assets': self.get_dates_metrics_total_count_active_assets(),
            })

        if _all or query_params.get('dates_login_times_top10_assets'):
            data.update({
                'dates_login_times_top10_assets': self.get_dates_login_times_assets(),
            })

        if _all or query_params.get('dates_login_times_top10_users'):
            data.update({
                'dates_login_times_top10_users': self.get_dates_login_times_users(),
            })

        if _all or query_params.get('dates_login_record_top10_sessions'):
            data.update({
                'dates_login_record_top10_sessions': self.get_dates_login_record_sessions()
            })

        return JsonResponse(data, status=200)


class HealthApiMixin(APIView):
    pass


class HealthCheckView(HealthApiMixin):
    permission_classes = (AllowAny,)

    @staticmethod
    def get_db_status():
        t1 = time.time()
        try:
            ok = User.objects.first() is not None
            t2 = time.time()
            return ok, t2 - t1
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_redis_status():
        key = 'HEALTH_CHECK'

        t1 = time.time()
        try:
            value = '1'
            cache.set(key, '1', 10)
            got = cache.get(key)
            t2 = time.time()

            if value == got:
                return True, t2 - t1
            return False, 'Value not match'
        except Exception as e:
            return False, str(e)

    def get(self, request):
        redis_status, redis_time = self.get_redis_status()
        db_status, db_time = self.get_db_status()
        status = all([redis_status, db_status])
        data = {
            'status': status,
            'db_status': db_status,
            'db_time': db_time,
            'redis_status': redis_status,
            'redis_time': redis_time,
            'time': int(time.time()),
        }
        return Response(data)


class PrometheusMetricsApi(HealthApiMixin):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        util = ComponentsPrometheusMetricsUtil()
        metrics_text = util.get_prometheus_metrics_text()
        return HttpResponse(metrics_text, content_type='text/plain; version=0.0.4; charset=utf-8')
