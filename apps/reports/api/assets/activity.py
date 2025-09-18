# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import Count
from django.http.response import JsonResponse
from rest_framework.views import APIView

from assets.const import AllTypes
from assets.models import Asset
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from rbac.permissions import RBACPermission
from reports.api.assets.base import group_stats
from reports.mixins import DateRangeMixin
from terminal.const import LoginFrom
from terminal.models import Session

__all__ = ['AssetActivityApi']


class AssetActivityApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'rbac.view_assetactivityreport',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    def get_asset_login_metrics(self, queryset):
        data = defaultdict(set)
        for t, _id in queryset.values_list('date_start', 'id'):
            date_str = str(t.date())
            data[date_str].add(_id)

        metrics = [len(data.get(str(d), set())) for d in self.date_range_list]
        return metrics

    @lazyproperty
    def session_qs(self):
        return Session.objects.all()

    def get(self, request, *args, **kwargs):
        qs = self.session_qs
        qs = self.filter_by_date_range(qs, 'date_start')
        all_type_dict = dict(AllTypes.choices())

        stats = qs.aggregate(
            total=Count(1),
            asset_count=Count('asset_id', distinct=True),
            user_count=Count('user_id', distinct=True),
        )

        asset_ids = {str(_id) for _id in qs.values_list('asset_id', flat=True).distinct()}
        assets = Asset.objects.filter(id__in=asset_ids)

        asset_login_by_protocol = group_stats(
            qs, 'label', 'protocol'
        )

        asset_login_by_from = group_stats(
            qs, 'label', 'login_from', LoginFrom.as_dict()
        )

        asset_by_type = group_stats(
            assets, 'label', 'platform__type', all_type_dict,
        )

        payload = {
            'session_stats': stats,
            'asset_login_by_type': asset_by_type,
            'asset_login_by_from': asset_login_by_from,
            'asset_login_by_protocol': asset_login_by_protocol,
            'asset_login_log_metrics': {
                'dates_metrics_date': self.dates_metrics_date,
                'dates_metrics_total': self.get_asset_login_metrics(qs),
            }
        }
        return JsonResponse(payload, status=200)
