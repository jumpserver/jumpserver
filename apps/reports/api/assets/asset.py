# -*- coding: utf-8 -*-
#

from django.db.models import Count, Q, F
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView

from assets.const import AllTypes, Connectivity, Category
from assets.models import Asset
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from rbac.permissions import RBACPermission

__all__ = ['AssetStatisticApi']


class AssetStatisticApi(APIView):
    http_method_names = ['get']
    # TODO: Define the required RBAC permissions for this API
    rbac_perms = {
        'GET': 'assets.view_asset',
    }
    permission_classes = [RBACPermission, IsValidLicense]

    @lazyproperty
    def base_qs(self):
        return Asset.objects.only(
            'id', 'platform', 'zone', 'connectivity', 'created_time'
        )

    @staticmethod
    def _group_stats(queryset, alias, key, label_map=None):
        grouped = (
            queryset
            .values(**{alias: F(key)})
            .annotate(total=Count('id'))
        )

        data = [
            {
                alias: val,
                'total': cnt,
                **({'label': label_map.get(val, val)} if label_map else {})
            }
            for val, cnt in grouped.values_list(alias, 'total')
        ]

        return data

    def get(self, request, *args, **kwargs):
        qs = self.base_qs

        stats = qs.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            connected=Count('id', filter=Q(connectivity=Connectivity.OK)),
        )

        by_type = self._group_stats(
            qs, 'type', 'platform__type', dict(AllTypes.choices()),
        )

        by_category = self._group_stats(
            qs, 'category', 'platform__category', dict(Category.choices())
        )

        by_zone = self._group_stats(
            qs, 'zone', 'zone__name'
        )

        week_start = timezone.now() + timezone.timedelta(days=7)
        assets_added_this_week = qs.filter(date_created__gte=week_start).count()
        payload = {
            **stats,
            'assets_by_platform_type': by_type,
            'assets_by_category': by_category,
            'assets_by_zone': by_zone,
            'assets_added_this_week': assets_added_this_week,
        }
        return JsonResponse(payload, status=200)
