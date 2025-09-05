# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import Count, Q
from django.http.response import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView

from audits.const import LoginStatusChoices
from audits.models import UserLoginLog
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from rbac.permissions import RBACPermission
from reports.mixins import DateRangeMixin
from users.models import User, Source

__all__ = ['UserReportApi']


class UserReportApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'rbac.view_userloginreport',
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

    def get_user_login_method_metrics(self, source_map):
        filtered_queryset = self.filter_by_date_range(self.user_login_log_queryset, 'datetime')

        backends = set()
        data = defaultdict(lambda: defaultdict(set))
        for t, username, backend in filtered_queryset.values_list('datetime', 'username', 'backend'):
            backend = str(source_map.get(backend.lower(), backend))
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

    def get_user_login_time_metrics(self):
        buckets = ['00:00-06:00', '06:00-12:00', '12:00-18:00', '18:00-24:00']
        metrics = {k: 0 for k in buckets}

        qs = self.filter_by_date_range(self.user_login_log_queryset, 'datetime').only('datetime')

        for obj in qs:
            dt = obj.datetime
            dt_local = timezone.localtime(dt)
            hour = dt_local.hour
            metrics[buckets[hour // 6]] += 1

        return metrics

    @lazyproperty
    def user_login_log_queryset(self):
        queryset = UserLoginLog.objects.filter(status=LoginStatusChoices.success)
        return UserLoginLog.filter_queryset_by_org(queryset)

    @lazyproperty
    def user_login_failed_queryset(self):
        queryset = UserLoginLog.objects.filter(status=LoginStatusChoices.failed)
        return UserLoginLog.filter_queryset_by_org(queryset)

    @lazyproperty
    def user_qs(self):
        return User.get_org_users()

    def get(self, request, *args, **kwargs):
        data = {}

        user_stats = self.user_qs.aggregate(
            total=Count(1),
            first_login=Count(1, filter=Q(is_first_login=True)),
            need_update_password=Count(1, filter=Q(need_update_password=True)),
            face_vector=Count(1, filter=Q(face_vector__isnull=False)),
            not_enabled_mfa=Count(1, filter=Q(mfa_level=0)),
        )

        user_stats['valid'] = sum(1 for u in self.user_qs if u.is_valid)
        data['user_stats'] = user_stats

        source_map = Source.as_dict()
        source_map.update({'password': _('Password')})
        user_by_source = defaultdict(int)
        for source in self.user_qs.values_list('source', flat=True):
            k = source_map.get(source, source)
            user_by_source[str(k)] += 1

        data['user_by_source'] = [{'name': k, 'value': v} for k, v in user_by_source.items()]

        data['user_login_log_metrics'] = {
            'dates_metrics_date': self.dates_metrics_date,
            'dates_metrics_success_total': self.get_user_login_metrics(self.user_login_log_queryset),
            'dates_metrics_failure_total': self.get_user_login_metrics(self.user_login_failed_queryset),
        }
        data['user_login_method_metrics'] = {
            'dates_metrics_date': self.dates_metrics_date,
            'dates_metrics_total': self.get_user_login_method_metrics(source_map),
        }
        data['user_login_time_metrics'] = self.get_user_login_time_metrics()
        return JsonResponse(data, status=200)
