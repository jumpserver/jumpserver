# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import Count
from django.http.response import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView

from audits.const import LoginStatusChoices
from audits.models import UserLoginLog
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from common.utils.timezone import local_zero_hour, local_now
from rbac.permissions import RBACPermission

__all__ = ['UserReportApi']


class UserReportApi(APIView):
    http_method_names = ['get']
    # TODO: Define the required RBAC permissions for this API
    rbac_perms = {
    }
    permission_classes = [RBACPermission, IsValidLicense]

    @lazyproperty
    def days(self):
        count = self.request.query_params.get('days', 1)
        return int(count)

    @property
    def days_to_datetime(self):
        if self.days == 1:
            return local_zero_hour()
        return local_now() - timezone.timedelta(days=self.days)

    @lazyproperty
    def date_range_list(self):
        return [
            (local_now() - timezone.timedelta(days=i)).date()
            for i in range(self.days - 1, -1, -1)
        ]

    def filter_by_date_range(self, queryset, field_name):
        date_range_bounds = self.days_to_datetime.date(), (local_now() + timezone.timedelta(days=1)).date()
        return queryset.filter(**{f'{field_name}__range': date_range_bounds})

    def get_user_login_metrics(self):
        filtered_queryset = self.filter_by_date_range(self.user_login_log_queryset, 'datetime')

        data = defaultdict(set)
        for t, username in filtered_queryset.values_list('datetime', 'username'):
            date_str = str(t.date())
            data[date_str].add(username)

        metrics = [len(v) for __, v in data]
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
        for backend in backends:
            for date_str, usernames in data.items():
                metrics[backend].append(len(usernames.get(backend, set())))
        return metrics

    def get_user_login_region_distribution(self):
        filtered_queryset = self.filter_by_date_range(self.user_login_log_queryset, 'datetime')

        data = filtered_queryset.values('city').annotate(
            user_count=Count('username', distinct=True)
        ).order_by('-user_count')
        return list(data)

    @lazyproperty
    def user_login_log_queryset(self):
        queryset = UserLoginLog.objects.filter(status=LoginStatusChoices.success)
        return UserLoginLog.filter_login_queryset_by_org(queryset)

    def get(self, request, *args, **kwargs):
        query_params = self.request.query_params
        data = {}

        _all = query_params.get('all')

        if _all or query_params.get('user_login_log_metrics'):
            metrics = self.get_user_login_metrics()
            data.update({
                'dates_metrics_date': [date.strftime('%m-%d') for date in self.date_range_list] or ['0'],
                'dates_metrics_total': metrics,
            })

        if _all or query_params.get('user_login_method_metrics'):
            metrics = self.get_user_login_method_metrics()
            data.update({
                'dates_metrics_date': [date.strftime('%m-%d') for date in self.date_range_list] or ['0'],
                'dates_metrics_total': metrics,
            })

        if _all or query_params.get('user_login_region_distribution'):
            data.update({
                'user_login_region_distribution': self.get_user_login_region_distribution(),
            })

        return JsonResponse(data, status=200)
