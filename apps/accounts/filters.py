# -*- coding: utf-8 -*-
#
import uuid

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as drf_filters
from rest_framework import filters
from rest_framework.compat import coreapi

from assets.const import AllTypes, Category
from assets.models import Asset, Node
from assets.utils import get_node_from_request
from common.drf.filters import BaseFilterSet
from common.utils import get_logger
from common.utils.timezone import local_zero_hour, local_now
from .const.automation import (
    ChangeSecretAccountStatus, ChangeSecretRecordStatusChoice,
)
from .const.account import Source
from .models import (
    Account, AccountRisk, AutomationExecution, BackupAccountAutomation,
    ChangeSecretAutomation, ChangeSecretRecord, CheckAccountAutomation,
    GatheredAccount, IntegrationApplication,
    PushSecretRecord, RiskChoice,
)
from .utils import account_secret_task_status

logger = get_logger(__file__)


class UUIDFilterMixin:
    @staticmethod
    def filter_uuid(queryset, name, value):
        try:
            uuid.UUID(value)
        except ValueError:
            logger.warning(f"Invalid UUID: {value}")
            return queryset.none()

        return queryset.filter(**{name: value})


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


class ChoiceInFilter(drf_filters.BaseInFilter, drf_filters.ChoiceFilter):
    pass


class BackupAccountFilterSet(BaseFilterSet):
    class Meta:
        model = BackupAccountAutomation
        fields = ["id", "name", "backup_type"]


class ChangeSecretAutomationFilterSet(BaseFilterSet):
    class Meta:
        model = ChangeSecretAutomation
        fields = ["id", "name", "secret_type", "secret_strategy"]


class CheckAccountAutomationFilterSet(BaseFilterSet):
    class Meta:
        model = CheckAccountAutomation
        fields = ["id", "name"]


class AccountRiskFilterSet(BaseFilterSet):
    asset_id = drf_filters.UUIDFilter(
        field_name="asset__id", label=_("Asset ID")
    )
    asset_name = drf_filters.CharFilter(
        field_name="asset__name", label=_("Asset name")
    )

    class Meta:
        model = AccountRisk
        fields = [
            "id", "username", "asset_id", "asset_name", "risk", "status",
        ]


class IntegrationApplicationFilterSet(BaseFilterSet):
    class Meta:
        model = IntegrationApplication
        fields = ["id", "name", "is_active", "comment"]


class AutomationAssetFilterSet(BaseFilterSet):
    class Meta:
        model = Asset
        fields = ["id", "name", "address"]


class AccountFilterSet(UUIDFilterMixin, BaseFilterSet):
    address = drf_filters.CharFilter(
        field_name="asset__address", label=_("Asset address")
    )
    asset_name = drf_filters.CharFilter(
        field_name="asset__name", label=_("Asset name")
    )
    asset_id = drf_filters.CharFilter(
        field_name="asset_id", method="filter_uuid", label=_("Asset ID")
    )
    has_secret = drf_filters.BooleanFilter(
        method="filter_has_secret", label=_("Has secret")
    )
    platform = drf_filters.CharFilter(
        field_name="asset__platform_id", lookup_expr="exact",
        label=_("Platform ID")
    )
    category = drf_filters.ChoiceFilter(
        field_name="asset__platform__category", lookup_expr="exact",
        label=_("Platform category"),
        choices=Category.choices
    )
    type = drf_filters.ChoiceFilter(
        field_name="asset__platform__type", lookup_expr="exact",
        label=_("Platform type"),
        choices=AllTypes.choices()
    )
    source = drf_filters.ChoiceFilter(
        label=_("Source"), choices=Source.choices
    )
    latest_discovery = drf_filters.BooleanFilter(
        method="filter_latest", label=_("Recently discovered")
    )
    latest_accessed = drf_filters.BooleanFilter(
        method="filter_latest", label=_("Recently accessed")
    )
    latest_updated = drf_filters.BooleanFilter(
        method="filter_latest", label=_("Recently updated")
    )
    latest_secret_changed = drf_filters.BooleanFilter(
        method="filter_latest", label=_("Recently changed secret")
    )
    latest_secret_change_failed = drf_filters.BooleanFilter(
        method="filter_latest", label=_("Recent secret change failed")
    )
    risk = ChoiceInFilter(
        method="filter_risk", choices=RiskChoice.choices, label=_("Risk")
    )
    integrationapplication = drf_filters.CharFilter(
        method="filter_integrationapplication",
        label=_("Integration application ID")
    )
    long_time_no_change_secret = drf_filters.BooleanFilter(
        method="filter_long_time", label=_("Long time no secret change")
    )
    long_time_no_login = drf_filters.BooleanFilter(
        method="filter_long_time", label=_("Long time no login")
    )
    long_time_no_verified = drf_filters.BooleanFilter(
        method="filter_long_time", label=_("Long time no verification")
    )

    class Meta:
        model = Account
        fields = [
            "id", "name", "username",
            "address", "asset_name", "asset_id", "connectivity",
            "privileged", "is_active",
            "secret_type", "category", "type", "platform",
            "secret_reset", "source", "source_id",
            "has_secret", "risk", "integrationapplication",
            "latest_discovery", "latest_accessed", "latest_updated",
            "latest_secret_changed", "latest_secret_change_failed",
            "long_time_no_change_secret", "long_time_no_login",
            "long_time_no_verified",
        ]
        fields_operator = {
            "risk": ("exact", "in"),
        }

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
        elif name == "long_time_no_login":
            field = "date_last_login"
            confirm_field = None
        else:
            field = "date_verified"
            confirm_field = "connectivity"

        q = Q(**{f"{field}__lt": date}) | Q(**{f"{field}__isnull": True})
        confirm_q = {f"{confirm_field}": "na"} if confirm_field else {}
        queryset = queryset.exclude(**confirm_q).filter(q)
        return queryset

    @staticmethod
    def filter_risk(queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(risks__risk__in=value).distinct()

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
            queryset = (
                queryset.filter(date_change_secret__gt=date)
                .exclude(change_secret_status=ChangeSecretRecordStatusChoice.success)
            )

        if kwargs:
            queryset = queryset.filter(**kwargs)
        return queryset



class GatheredAccountFilterSet(BaseFilterSet):
    asset_id = drf_filters.UUIDFilter(
        field_name="asset__id", label=_("Asset ID")
    )
    asset_name = drf_filters.CharFilter(
        field_name="asset__name", lookup_expr="icontains",
        label=_("Asset name")
    )
    status = drf_filters.CharFilter(
        field_name="status", lookup_expr="exact", label=_("Status")
    )

    class Meta:
        model = GatheredAccount
        fields = [
            "id", "username", "asset_name", "asset_id", "status",
        ]


class SecretRecordMixin(drf_filters.FilterSet):
    asset_id = drf_filters.UUIDFilter(
        field_name="asset__id", label=_("Asset ID")
    )
    asset_name = drf_filters.CharFilter(
        field_name="asset__name", label=_("Asset name")
    )
    account_username = drf_filters.CharFilter(
        field_name="account__username", label=_("Account username")
    )
    execution_id = drf_filters.UUIDFilter(
        field_name="execution_id", label=_("Execution ID")
    )
    days = drf_filters.NumberFilter(
        method="filter_days", label=_("Days")
    )

    @staticmethod
    def filter_days(queryset, name, value):
        value = int(value)

        dt = local_zero_hour()
        if value != 1:
            dt = local_now() - timezone.timedelta(days=value)
        return queryset.filter(date_finished__gte=dt)


class DaysExecutionFilterMixin:
    days = drf_filters.NumberFilter(
        method="filter_days", label=_("Days")
    )
    field: str

    def filter_days(self, queryset, name, value):
        value = int(value)

        dt = local_zero_hour()
        if value != 1:
            dt = local_now() - timezone.timedelta(days=value)
        return queryset.filter(**{f'{self.field}__gte': dt})


class ChangeSecretRecordFilterSet(SecretRecordMixin, BaseFilterSet):
    status = drf_filters.ChoiceFilter(
        choices=ChangeSecretRecordStatusChoice.choices, label=_("Status")
    )

    class Meta:
        model = ChangeSecretRecord
        fields = [
            "id", "status", "asset_id", "asset_name",
            "account_username", "execution_id",
        ]


class AutomationExecutionFilterSet(DaysExecutionFilterMixin, BaseFilterSet):
    automation_id = drf_filters.UUIDFilter(
        field_name="automation_id", label=_("Task ID")
    )
    automation_name = drf_filters.CharFilter(
        field_name="automation__name", label=_("Task name")
    )
    field = 'date_start'

    class Meta:
        model = AutomationExecution
        fields = [
            "id", "automation_id", "automation_name",
            "status", "trigger",
        ]


class PushAccountRecordFilterSet(SecretRecordMixin, BaseFilterSet):
    status = drf_filters.ChoiceFilter(
        field_name='status', choices=ChangeSecretRecordStatusChoice.choices,
        label=_("Status")
    )

    class Meta:
        model = PushSecretRecord
        fields = [
            "id", "status", "asset_id", "asset_name",
            "account_username", "execution_id",
        ]


class ChangeSecretStatusFilterSet(BaseFilterSet):
    asset_name = drf_filters.CharFilter(
        field_name="asset__name", label=_("Asset name")
    )
    status = drf_filters.ChoiceFilter(
        method='filter_dynamic', choices=ChangeSecretAccountStatus.choices,
        label=_("Status")
    )
    execution_id = drf_filters.CharFilter(
        method='filter_dynamic', label=_("Execution ID")
    )

    class Meta:
        model = Account
        fields = [
            "id", "username", "asset_name", "status", "execution_id",
        ]

    @staticmethod
    def filter_dynamic(queryset, name, value):
        _ids = list(queryset.values_list('id', flat=True))
        data_map = {
            _id: account_secret_task_status.get(str(_id)).get(name)
            for _id in _ids
        }
        matched = [_id for _id, v in data_map.items() if v == value]
        return queryset.filter(id__in=matched)
