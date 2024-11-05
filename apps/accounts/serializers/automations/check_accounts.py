# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import AutomationTypes
from accounts.models import AccountCheckAutomation, AccountRisk, RiskChoice
from assets.models import Asset
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.utils import get_logger
from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = [
    'CheckAccountsAutomationSerializer',
    'AccountRiskSerializer',
    'AccountCheckEngineSerializer',
    'AssetRiskSerializer',
]


class AccountRiskSerializer(serializers.ModelSerializer):
    asset = ObjectRelatedField(queryset=Asset.objects.all(), required=False,label=_("Asset"))
    risk = LabeledChoiceField(choices=RiskChoice.choices, required=False, read_only=True, label=_("Risk"))

    class Meta:
        model = AccountRisk
        fields = [
            'id', 'asset', 'username', 'risk', 'confirmed',
            'date_created'
        ]


class RiskSummarySerializer(serializers.Serializer):
    risk = serializers.CharField(max_length=128)
    count = serializers.IntegerField()


class AssetRiskSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=128, required=False, source='asset__id')
    name = serializers.CharField(max_length=128, required=False, source='asset__name')
    address = serializers.CharField(max_length=128, required=False, source='asset__address')
    platform = serializers.CharField(max_length=128, required=False, source='asset__platform__name')
    risk_total = serializers.IntegerField()
    risk_summary = serializers.SerializerMethodField()

    @staticmethod
    def get_risk_summary(obj):
        summary = {}
        for risk in RiskChoice.choices:
            summary[f'{risk[0]}_count'] = obj.get(f'{risk[0]}_count', 0)
        return summary


class CheckAccountsAutomationSerializer(BaseAutomationSerializer):
    class Meta:
        model = AccountCheckAutomation
        read_only_fields = BaseAutomationSerializer.Meta.read_only_fields
        fields = BaseAutomationSerializer.Meta.fields \
                 + [] + read_only_fields
        extra_kwargs = BaseAutomationSerializer.Meta.extra_kwargs

    @property
    def model_type(self):
        return AutomationTypes.check_account


class AccountCheckEngineSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=128, required=True)
    display_name = serializers.CharField(max_length=128, required=False)
    description = serializers.CharField(required=False)
