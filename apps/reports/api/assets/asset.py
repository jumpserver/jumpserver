# -*- coding: utf-8 -*-
#
from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework.views import APIView

from assets.const import Connectivity
from assets.models import Asset, Platform
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from rbac.permissions import RBACPermission
from reports.mixins import DateRangeMixin, aggregate_by_date, asset_type_category_counts

__all__ = ['AssetStatisticApi']


class AssetStatisticApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'rbac.view_assetstatisticsreport',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    @lazyproperty
    def base_qs(self):
        return Asset.objects.all()

    def get_added_asset_metrics(self):
        filtered_queryset = self.filter_by_date_range(self.base_qs, 'date_created')

        data = aggregate_by_date(
            filtered_queryset, 'date_created', self.date_range_list,
            total=Count('id', distinct=True),
        )
        return [data[day]['total'] for day in self.date_range_list]

    def get(self, request, *args, **kwargs):
        qs = self.base_qs
        stats = qs.aggregate(
            total=Count(1),
            active=Count(1, filter=Q(is_active=True)),
            connected=Count(1, filter=Q(connectivity=Connectivity.OK)),
            zone=Count(1, filter=Q(zone__isnull=False)),
            directory_services=Count(1, filter=Q(directory_services__isnull=False)),
        )

        sorted_category_assets = asset_type_category_counts(qs)

        stats.update({
            'platform_count': Platform.objects.all().count(),
        })

        payload = {
            'asset_stats': stats,
            'assets_by_type_category': sorted_category_assets,
            'added_asset_metrics': {
                'dates_metrics_date': self.dates_metrics_date,
                'dates_metrics_total': self.get_added_asset_metrics(),
            }
        }
        return JsonResponse(payload, status=200)
