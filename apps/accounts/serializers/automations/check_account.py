# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import AutomationTypes
from accounts.models import (
    CheckAccountAutomation,
    AccountRisk,
    RiskChoice,
    CheckAccountEngine,
)
from accounts.risk_handlers import TYPE_CHOICES
from assets.models import Asset
from common.const import ConfirmOrIgnore
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.utils import get_logger
from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = [
    "CheckAccountAutomationSerializer",
    "AccountRiskSerializer",
    "CheckAccountEngineSerializer",
    "AssetRiskSerializer",
    "HandleRiskSerializer",
]


class AccountRiskSerializer(serializers.ModelSerializer):
    asset = ObjectRelatedField(
        queryset=Asset.objects.all(), required=False, label=_("Asset")
    )
    risk = LabeledChoiceField(
        choices=RiskChoice.choices, required=False, read_only=True, label=_("Risk")
    )
    status = LabeledChoiceField(
        choices=ConfirmOrIgnore.choices, required=False, label=_("Status")
    )

    class Meta:
        model = AccountRisk
        fields = [
            "id", "asset", "username", "risk", "status",
            "date_created", "details",
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.select_related("asset")


class RiskSummarySerializer(serializers.Serializer):
    risk = serializers.CharField(max_length=128)
    count = serializers.IntegerField()


class AssetRiskSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=128, required=False, source="asset__id")
    name = serializers.CharField(max_length=128, required=False, source="asset__name")
    address = serializers.CharField(
        max_length=128, required=False, source="asset__address"
    )
    platform = serializers.CharField(
        max_length=128, required=False, source="asset__platform__name"
    )
    risk_total = serializers.IntegerField()
    risk_summary = serializers.SerializerMethodField()

    @staticmethod
    def get_risk_summary(obj):
        summary = {}
        for risk in RiskChoice.choices:
            summary[f"{risk[0]}_count"] = obj.get(f"{risk[0]}_count", 0)
        return summary


class HandleRiskSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=128)
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects)
    action = serializers.ChoiceField(choices=TYPE_CHOICES)
    risk = serializers.ChoiceField(choices=RiskChoice.choices, allow_null=True, allow_blank=True)


class CheckAccountAutomationSerializer(BaseAutomationSerializer):
    class Meta:
        model = CheckAccountAutomation
        read_only_fields = BaseAutomationSerializer.Meta.read_only_fields
        fields = (
                BaseAutomationSerializer.Meta.fields
                + ["engines", "recipients"]
                + read_only_fields
        )
        extra_kwargs = BaseAutomationSerializer.Meta.extra_kwargs

    @property
    def model_type(self):
        return AutomationTypes.check_account

    @staticmethod
    def validate_engines(engines):
        valid_slugs = {i['slug'] for i in CheckAccountEngine.get_default_engines()}

        if not all(engine in valid_slugs for engine in engines):
            raise serializers.ValidationError(_("Invalid engine id"))

        return engines


class CheckAccountEngineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckAccountEngine
        fields = ["id", "name", "slug", "comment"]
        read_only_fields = ["slug"]
