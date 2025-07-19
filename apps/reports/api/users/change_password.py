# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import Count
from django.http.response import JsonResponse
from rest_framework.views import APIView

from audits.models import PasswordChangeLog
from common.permissions import IsValidLicense
from common.utils import lazyproperty, get_ip_city, get_logger
from rbac.permissions import RBACPermission
from reports.mixins import DateRangeMixin

__all__ = ['UserChangeSecretApi']

logger = get_logger(__file__)


class UserChangeSecretApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    # TODO: Define the required RBAC permissions for this API
    rbac_perms = {
        'GET': 'users..view_users',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    @staticmethod
    def get_change_password_region_distribution(queryset):
        unique_ips = queryset.values_list('remote_addr', flat=True).distinct()
        data = defaultdict(int)
        for ip in unique_ips:
            try:
                city = str(get_ip_city(ip))
                if not city:
                    continue
                data[city] += 1
            except Exception:
                logger.debug(f"Failed to get city for IP {ip}, skipping", exc_info=True)
                continue
        return dict(data)

    def get_change_password_metrics(self, queryset):
        filtered_queryset = self.filter_by_date_range(queryset, 'datetime')

        data = defaultdict(set)
        for t, username in filtered_queryset.values_list('datetime', 'user'):
            date_str = str(t.date())
            data[date_str].add(username)

        metrics = [len(data.get(str(d), set())) for d in self.date_range_list]
        return metrics

    @lazyproperty
    def change_password_queryset(self):
        queryset = PasswordChangeLog.objects.all()
        return PasswordChangeLog.filter_queryset_by_org(queryset)

    def get(self, request, *args, **kwargs):
        data = {}
        dates_metrics_date = [date.strftime('%m-%d') for date in self.date_range_list] or ['0']

        qs = self.filter_by_date_range(self.change_password_queryset, 'datetime')

        total = qs.count()
        change_password_top10_users = qs.values(
            'user').annotate(user_count=Count('id')).order_by('-user_count')[:10]

        change_password_top10_change_bys = qs.values(
            'change_by').annotate(user_count=Count('id')).order_by('-user_count')[:10]

        data['total'] = total
        data['user_total'] = qs.values('user').distinct().count()
        data['change_by_total'] = qs.values('change_by').distinct().count()
        data['change_password_top10_users'] = list(change_password_top10_users)
        data['change_password_top10_change_bys'] = list(change_password_top10_change_bys)

        data['user_change_password_metrics'] = {
            'dates_metrics_date': dates_metrics_date,
            'dates_metrics_total': self.get_change_password_metrics(qs),
        }

        data['change_password_region_distribution'] = self.get_change_password_region_distribution(qs)
        return JsonResponse(data, status=200)
