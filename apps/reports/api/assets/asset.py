# -*- coding: utf-8 -*-
#
from collections import defaultdict, OrderedDict

from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework.views import APIView

from assets.const import AllTypes, Connectivity
from assets.models import Asset, Platform
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from rbac.permissions import RBACPermission
from reports.api.assets.base import group_stats
from reports.mixins import DateRangeMixin

__all__ = ['AssetStatisticApi']


class AssetStatisticApi(DateRangeMixin, APIView):
    http_method_names = ['get']
    rbac_perms = {
        'GET': 'assets.view_asset',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    @lazyproperty
    def base_qs(self):
        return Asset.objects.all()

    def get_added_asset_metrics(self):
        filtered_queryset = self.filter_by_date_range(self.base_qs, 'date_created')

        data = defaultdict(set)
        for t, _id in filtered_queryset.values_list('date_created', 'id'):
            date_str = str(t.date())
            data[date_str].add(_id)

        metrics = [len(data.get(str(d), set())) for d in self.date_range_list]
        return metrics

    def get(self, request, *args, **kwargs):
        qs = self.base_qs
        all_type_dict = dict(AllTypes.choices())

        stats = qs.aggregate(
            total=Count(1),
            active=Count(1, filter=Q(is_active=True)),
            connected=Count(1, filter=Q(connectivity=Connectivity.OK)),
            zone=Count(1, filter=Q(zone__isnull=False)),
            directory_services=Count(1, filter=Q(directory_services__isnull=False)),
        )

        type_category_map = {
            d['label']: str(d['category'].label)
            for d in AllTypes.types()
        }

        by_type = group_stats(
            qs, 'type', 'platform__type', all_type_dict,
        )

        by_type_category = defaultdict(list)
        for item in by_type:
            category = type_category_map.get(item['label'], 'Other')
            by_type_category[category].append(item)

        sorted_category_assets = OrderedDict()
        desired_order = [str(i['label']) for i in AllTypes.categories()]
        for category in desired_order:
            sorted_category_assets[category] = by_type_category.get(category, [])

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
