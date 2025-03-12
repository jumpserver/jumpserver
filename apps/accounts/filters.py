# -*- coding: utf-8 -*-
#
from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as drf_filters
from rest_framework import filters
from rest_framework.compat import coreapi

from assets.models import Node
from assets.utils import get_node_from_request
from common.drf.filters import BaseFilterSet
from common.utils.timezone import local_zero_hour, local_now
from .const.automation import ChangeSecretRecordStatusChoice
from .models import Account, GatheredAccount, ChangeSecretRecord, PushSecretRecord, IntegrationApplication


class NodeFilterBackend(filters.BaseFilterBackend):
    fields = ['node_id']

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name=field, location='query', required=False,
                type='string', example='', description='', schema=None,
            )
            for field in self.fields
        ]

    def filter_queryset(self, request, queryset, view):
        node = get_node_from_request(request)
        if node is None:
            return queryset

        node_qs = Node.objects.none()
        node_qs |= node.get_all_children(with_self=True)
        node_ids = list(node_qs.values_list("id", flat=True))
        queryset = queryset.filter(asset__nodes__in=node_ids)
        return queryset


class AccountFilterSet(BaseFilterSet):
    ip = drf_filters.CharFilter(field_name="address", lookup_expr="exact")
    hostname = drf_filters.CharFilter(field_name="name", lookup_expr="exact")
    username = drf_filters.CharFilter(field_name="username", lookup_expr="exact")
    address = drf_filters.CharFilter(field_name="asset__address", lookup_expr="exact")
    asset_id = drf_filters.CharFilter(field_name="asset", lookup_expr="exact")
    asset = drf_filters.CharFilter(field_name="asset", lookup_expr="exact")
    assets = drf_filters.CharFilter(field_name="asset_id", lookup_expr="exact")
    has_secret = drf_filters.BooleanFilter(method="filter_has_secret")
    platform = drf_filters.CharFilter(
        field_name="asset__platform_id", lookup_expr="exact"
    )
    category = drf_filters.CharFilter(
        field_name="asset__platform__category", lookup_expr="exact"
    )
    type = drf_filters.CharFilter(
        field_name="asset__platform__type", lookup_expr="exact"
    )
    latest_discovery = drf_filters.BooleanFilter(method="filter_latest")
    latest_accessed = drf_filters.BooleanFilter(method="filter_latest")
    latest_updated = drf_filters.BooleanFilter(method="filter_latest")
    latest_secret_changed = drf_filters.BooleanFilter(method="filter_latest")
    latest_secret_change_failed = drf_filters.BooleanFilter(method="filter_latest")
    risk = drf_filters.CharFilter(method="filter_risk")
    integrationapplication = drf_filters.CharFilter(method="filter_integrationapplication")
    long_time_no_change_secret = drf_filters.BooleanFilter(method="filter_long_time")
    long_time_no_verified = drf_filters.BooleanFilter(method="filter_long_time")

    @staticmethod
    def filter_has_secret(queryset, name, has_secret):
        q = Q(_secret__isnull=True) | Q(_secret="")
        if has_secret:
            return queryset.exclude(q)
        else:
            return queryset.filter(q)

    @staticmethod
    def filter_long_time(queryset, name, value):
        date = timezone.now() - timezone.timedelta(days=30)

        if name == "long_time_no_change_secret":
            field = "date_change_secret"
            confirm_field = "change_secret_status"
        else:
            field = "date_verified"
            confirm_field = "connectivity"

        q = Q(**{f"{field}__lt": date}) | Q(**{f"{field}__isnull": True})
        confirm_q = {f"{confirm_field}": "na"}
        queryset = queryset.exclude(**confirm_q).filter(q)
        return queryset

    @staticmethod
    def filter_risk(queryset, name, value):
        if not value:
            return queryset

        queryset = queryset.filter(risks__risk=value)
        return queryset

    @staticmethod
    def filter_integrationapplication(queryset, name, value):
        if not value:
            return queryset

        integrationapplication = IntegrationApplication.objects.filter(pk=value).first()
        if not integrationapplication:
            return IntegrationApplication.objects.none()
        return queryset & integrationapplication.get_accounts()

    @staticmethod
    def filter_latest(queryset, name, value):
        if not value:
            return queryset

        date = timezone.now() - timezone.timedelta(days=7)
        kwargs = {}

        if name == "latest_discovery":
            kwargs.update({"date_created__gte": date, "source": "collected"})
        elif name == "latest_accessed":
            kwargs.update({"date_last_login__gte": date})
        elif name == "latest_updated":
            kwargs.update({"date_updated__gte": date})
        elif name == "latest_secret_changed":
            kwargs.update({"date_change_secret__gt": date})

        if name == "latest_secret_change_failed":
            queryset = queryset.filter(date_change_secret__gt=date).exclude(
                change_secret_status=ChangeSecretRecordStatusChoice.success
            )

        if kwargs:
            queryset = queryset.filter(**kwargs)
        return queryset

    class Meta:
        model = Account
        fields = [
            "id", "asset", "source_id", "secret_type", "category",
            "type", "privileged", "secret_reset", "connectivity", 'is_active'
        ]


class GatheredAccountFilterSet(BaseFilterSet):
    asset_id = drf_filters.CharFilter(field_name="asset_id", lookup_expr="exact")
    asset_name = drf_filters.CharFilter(
        field_name="asset__name", lookup_expr="icontains"
    )
    status = drf_filters.CharFilter(field_name="status", lookup_expr="exact")

    class Meta:
        model = GatheredAccount
        fields = ["id", "username"]


class SecretRecordMixin(drf_filters.FilterSet):
    asset_name = drf_filters.CharFilter(
        field_name="asset__name", lookup_expr="icontains"
    )
    account_username = drf_filters.CharFilter(
        field_name="account__username", lookup_expr="icontains"
    )
    execution_id = drf_filters.CharFilter(
        field_name="execution_id", lookup_expr="exact"
    )
    days = drf_filters.NumberFilter(method="filter_days")

    @staticmethod
    def filter_days(queryset, name, value):
        value = int(value)

        dt = local_zero_hour()
        if value != 1:
            dt = local_now() - timezone.timedelta(days=value)
        return queryset.filter(date_finished__gte=dt)


class ChangeSecretRecordFilterSet(SecretRecordMixin, BaseFilterSet):
    class Meta:
        model = ChangeSecretRecord
        fields = ["id", "status", "asset_id", "execution"]


class PushAccountRecordFilterSet(SecretRecordMixin, BaseFilterSet):
    class Meta:
        model = PushSecretRecord
        fields = ["id", "status", "asset_id", "execution"]
