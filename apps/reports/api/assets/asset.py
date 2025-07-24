# -*- coding: utf-8 -*-
#

from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView

from assets.const import AllTypes, Connectivity, Category
from assets.models import Asset, Platform
from common.permissions import IsValidLicense
from common.utils import lazyproperty
from rbac.permissions import RBACPermission
from reports.api.assets.base import group_stats

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
            'id', 'platform', 'zone', 'connectivity', 'is_active'
        )

    def get(self, request, *args, **kwargs):
        qs = self.base_qs
        all_type_dict = dict(AllTypes.choices())

        platform_by_type = group_stats(
            Platform.objects.all(), 'type_label', 'type', all_type_dict,
        )

        stats = qs.aggregate(
            total=Count(1),
            active=Count(1, filter=Q(is_active=True)),
            connected=Count(1, filter=Q(connectivity=Connectivity.OK)),
        )

        by_type = group_stats(
            qs, 'type', 'platform__type', all_type_dict,
        )

        by_category = group_stats(
            qs, 'category', 'platform__category', Category.as_dict()
        )

        by_zone = group_stats(
            qs, 'zone_label', 'zone__name'
        )

        week_start = timezone.now() + timezone.timedelta(days=7)
        assets_added_this_week_qs = qs.filter(date_created__gte=week_start)
        assets_added_this_week_by_type = group_stats(
            assets_added_this_week_qs, 'type', 'platform__type', all_type_dict,
        )

        payload = {
            **stats,
            'platform_by_type': platform_by_type,
            'assets_by_type': by_type,
            'assets_by_category': by_category,
            'assets_by_zone': by_zone,
            'assets_added_this_week_count': assets_added_this_week_qs.count(),
            'assets_added_this_week_by_type': assets_added_this_week_by_type,
        }
        return JsonResponse(payload, status=200)
