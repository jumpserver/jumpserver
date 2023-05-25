from django_filters import rest_framework as drf_filters

from common.drf.filters import BaseFilterSet
from common.utils import is_uuid


class ACLFiltersetMixin(BaseFilterSet):
    users = drf_filters.CharFilter(method='filter_user')
    assets = drf_filters.CharFilter(method='filter_asset')

    @staticmethod
    def filter_user(queryset, name, value):
        from users.models import User
        if not value:
            return queryset
        if is_uuid(value):
            user = User.objects.filter(id=value).first()
        else:
            user = User.objects.filter(name=value).first()
        if not user:
            return queryset.none()
        q = queryset.model.users.get_filter_q(user)
        return queryset.filter(q).distinct()

    @staticmethod
    def filter_asset(queryset, name, value):
        from assets.models import Asset
        if not value:
            return queryset

        if is_uuid(value):
            asset = Asset.objects.filter(id=value).first()
        else:
            asset = Asset.objects.filter(name=value).first()
        if not asset:
            return queryset.none()

        q = queryset.model.assets.get_filter_q(asset)
        return queryset.filter(q).distinct()
