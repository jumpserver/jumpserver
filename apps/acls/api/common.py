from django.db.models import Q
from django_filters import rest_framework as drf_filters

from common.drf.filters import BaseFilterSet
from common.utils import is_uuid


class ACLUserFilterMixin(BaseFilterSet):
    users = drf_filters.CharFilter(method='filter_user')

    @staticmethod
    def filter_user(queryset, name, value):
        from users.models import User
        if not value:
            return queryset
        if is_uuid(value):
            user = User.objects.filter(id=value).first()
        else:
            q = Q(name=value) | Q(username=value)
            user = User.objects.filter(q).first()
        if not user:
            return queryset.none()
        q = queryset.model.users.get_filter_q(user)
        return queryset.filter(q).distinct()


class ACLUserAssetFilterMixin(ACLUserFilterMixin):
    assets = drf_filters.CharFilter(method='filter_asset')

    @staticmethod
    def filter_asset(queryset, name, value):
        from assets.models import Asset
        if not value:
            return queryset

        if is_uuid(value):
            asset = Asset.objects.filter(id=value).first()
        else:
            q = Q(name=value) | Q(address=value)
            asset = Asset.objects.filter(q).first()
        if not asset:
            return queryset.none()

        q = queryset.model.assets.get_filter_q(asset)
        return queryset.filter(q).distinct()
