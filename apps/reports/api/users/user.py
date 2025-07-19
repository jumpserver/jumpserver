# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import Count
from django.http.response import JsonResponse
from rest_framework.views import APIView

from audits.const import LoginStatusChoices
from audits.models import UserLoginLog
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from rbac.permissions import RBACPermission
from reports.mixins import DateRangeMixin

__all__ = ['UserReportApi']


class UserReportApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    # TODO: Define the required RBAC permissions for this API
    rbac_perms = {
        'GET': 'users..view_users',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    def get_user_login_metrics(self, queryset):
        filtered_queryset = self.filter_by_date_range(queryset, 'datetime')

        data = defaultdict(set)
        for t, username in filtered_queryset.values_list('datetime', 'username'):
            date_str = str(t.date())
            data[date_str].add(username)

        metrics = [len(data.get(str(d), set())) for d in self.date_range_list]
        return metrics

    def get_user_login_method_metrics(self):
        filtered_queryset = self.filter_by_date_range(self.user_login_log_queryset, 'datetime')

        backends = set()
        data = defaultdict(lambda: defaultdict(set))
        for t, username, backend in filtered_queryset.values_list('datetime', 'username', 'backend'):
            backends.add(backend)
            date_str = str(t.date())
            data[date_str][backend].add(username)
        metrics = defaultdict(list)
        for t in self.date_range_list:
            date_str = str(t)
            for backend in backends:
                username = data.get(date_str) if data.get(date_str) else {backend: set()}
                metrics[backend].append(len(username.get(backend, set())))
        return metrics

    def get_user_login_region_distribution(self):
        filtered_queryset = self.filter_by_date_range(self.user_login_log_queryset, 'datetime')

        data = filtered_queryset.values('city').annotate(
            user_count=Count('username', distinct=True)
        ).order_by('-user_count')
        metrics = [{'name': d['city'], 'value': d['user_count']} for d in data]
        return metrics

    def get_user_login_time_metrics(self):
        time_buckets = {
            '00:00-06:00': (0, 6),
            '06:00-12:00': (6, 12),
            '12:00-18:00': (12, 18),
            '18:00-24:00': (18, 24),
        }
        filtered_queryset = self.filter_by_date_range(self.user_login_log_queryset, 'datetime').all()
        metrics = {bucket: 0 for bucket in time_buckets.keys()}
        for date in filtered_queryset:
            hour = date.datetime.hour
            for bucket, (start, end) in time_buckets.items():
                if start <= hour < end:
                    metrics[bucket] = metrics.get(bucket, 0) + 1
        return metrics

    @lazyproperty
    def user_login_log_queryset(self):
        queryset = UserLoginLog.objects.filter(status=LoginStatusChoices.success)
        return UserLoginLog.filter_queryset_by_org(queryset)

    @lazyproperty
    def user_login_failed_queryset(self):
        queryset = UserLoginLog.objects.filter(status=LoginStatusChoices.failed)
        return UserLoginLog.filter_queryset_by_org(queryset)

    def get(self, request, *args, **kwargs):
        data = {}
        dates_metrics_date = [date.strftime('%m-%d') for date in self.date_range_list] or ['0']

        data['user_login_log_metrics'] = {
            'dates_metrics_date': dates_metrics_date,
            'dates_metrics_total': self.get_user_login_metrics(self.user_login_log_queryset),
        }
        data['user_login_failed_metrics'] = {
            'dates_metrics_date': dates_metrics_date,
            'dates_metrics_total': self.get_user_login_metrics(self.user_login_failed_queryset),
        }
        data['user_login_method_metrics'] = {
            'dates_metrics_date': dates_metrics_date,
            'dates_metrics_total': self.get_user_login_method_metrics(),
        }
        data['user_login_region_distribution'] = self.get_user_login_region_distribution()
        data['user_login_time_metrics'] = self.get_user_login_time_metrics()
        return JsonResponse(data, status=200)
