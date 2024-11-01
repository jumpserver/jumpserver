# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from accounts.const import AutomationTypes
from accounts.models import AccountCheckAutomation, AccountRisk
from common.utils import get_logger
from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = [
    'CheckAccountsAutomationSerializer',
    'AccountRiskSerializer',
    'AccountCheckEngineSerializer'
]


class AccountRiskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountRisk
        fields = '__all__'


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
