import time
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count, Max, F, CharField, Manager
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
from audits.backends import get_log_storage
from audits.const import LoginStatusChoices, LogType
from audits.models import JobLog
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

    @lazyproperty
    def users(self):
        return self.org.get_members()

    def get_logs_queryset(self, queryset, query_params):
        query = {}
        users = self.users
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
        qs = get_log_storage(LogType.login_log).get_manager().all()
        qs = self.get_logs_queryset_filter(qs, 'datetime')
        queryset = self.get_logs_queryset(qs, 'username')
        return queryset

    @lazyproperty
    def user_login_logs_on_the_system_queryset(self):
        qs = get_log_storage(LogType.login_log).get_manager().filter(
            status=LoginStatusChoices.success
        )
        qs = self.get_logs_queryset_filter(qs, 'datetime')
        queryset = qs.filter(username__in=construct_userlogin_usernames(self.users))
        return queryset

    @lazyproperty
    def password_change_logs_queryset(self):
        qs = get_log_storage(LogType.password_change_log).get_manager().all()
        qs = self.get_logs_queryset_filter(qs, 'datetime')
        queryset = self.get_logs_queryset(qs, 'user')
        return queryset

    @lazyproperty
    def operate_logs_queryset(self):
        qs = get_log_storage(LogType.operate_log).get_manager()
        return self.get_logs_queryset_filter(qs, 'datetime')

    @lazyproperty
    def ftp_logs_queryset(self):
        qs = get_log_storage(LogType.ftp_log).get_manager().all()
        return self.get_logs_queryset_filter(qs, 'date_start')

    @lazyproperty
    def command_type_queryset_tuple(self):
        type_queryset_tuple = Command.get_all_type_queryset_tuple()
        return (
            (tp, self.get_logs_queryset_filter(
                qs, 'timestamp', is_timestamp=True
            ))
            for tp, qs in type_queryset_tuple
        )

    @lazyproperty
    def job_logs_queryset(self):
        qs = JobLog.objects.all()
        return self.get_logs_queryset_filter(qs, 'date_start')


class DatesLoginMetricMixin:
    dates_list: list
    date_start_end: tuple
    command_type_queryset_tuple: tuple
    sessions_queryset: Manager
    ftp_logs_queryset: Manager
    job_logs_queryset: Manager
    login_logs_queryset: Manager
    user_login_logs_on_the_system_queryset: Manager
    operate_logs_queryset: Manager
    password_change_logs_queryset: Manager

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

    def get_date_metrics(self, queryset, field_name, count_fields):
        queryset = self.filter_date_start_end(queryset, field_name)

        if not isinstance(count_fields, (list, tuple)):
            count_fields = [count_fields]

        values_list = [field_name] + list(count_fields)
        queryset = queryset.values_list(*values_list)

        date_group_map = defaultdict(lambda: defaultdict(set))

        for row in queryset:
            datetime = row[0]
            date_str = str(datetime.date())
            for idx, count_field in enumerate(count_fields):
                date_group_map[date_str][count_field].add(row[idx + 1])

        date_metrics_dict = defaultdict(list)
        for field in count_fields:
            for date_str in self.dates_list:
                count = len(date_group_map.get(str(date_str), {}).get(field, set()))
                date_metrics_dict[field].append(count)

        return date_metrics_dict

    def get_dates_metrics_total_count_active_users_and_assets(self):
        date_metrics_dict = self.get_date_metrics(
            Session.objects, 'date_start', ('user_id', 'asset_id')
        )
        return date_metrics_dict.get('user_id', []), date_metrics_dict.get('asset_id', [])

    def get_dates_metrics_total_count_login(self):
        queryset = get_log_storage(LogType.login_log).get_manager()
        date_metrics_dict = self.get_date_metrics(
            queryset, 'datetime', 'id'
        )
        return date_metrics_dict.get('id', [])

    def get_dates_metrics_total_count_sessions(self):
        date_metrics_dict = self.get_date_metrics(
            Session.objects, 'date_start', 'id'
        )
        return date_metrics_dict.get('id', [])

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
        return self.user_login_logs_on_the_system_queryset.values('username').distinct().count()

    @lazyproperty
    def operate_logs_amount(self):
        return self.operate_logs_queryset.count()

    @lazyproperty
    def change_password_logs_amount(self):
        return self.password_change_logs_queryset.count()

    @lazyproperty
    def command_statistics(self):
        from terminal.const import CommandStorageType
        total_amount = 0
        danger_amount = 0
        for tp, qs in self.command_type_queryset_tuple:
            if tp == CommandStorageType.es:
                total_amount += qs.count(limit_to_max_result_window=False)
                danger_amount += qs.filter(risk_level=RiskLevelChoices.reject).count(limit_to_max_result_window=False)
            else:
                total_amount += qs.count()
                danger_amount += qs.filter(risk_level=RiskLevelChoices.reject).count()
        return total_amount, danger_amount

    @lazyproperty
    def commands_amount(self):
        total_amount, __ = self.command_statistics
        return total_amount

    @lazyproperty
    def commands_danger_amount(self):
        __, danger_amount = self.command_statistics
        return danger_amount

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
            user_data, asset_data = self.get_dates_metrics_total_count_active_users_and_assets()
            login_data = self.get_dates_metrics_total_count_login()
            data.update({
                'dates_metrics_date': self.get_dates_metrics_date(),
                'dates_metrics_total_count_login': login_data,
                'dates_metrics_total_count_active_users': user_data,
                'dates_metrics_total_count_active_assets': asset_data,
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
