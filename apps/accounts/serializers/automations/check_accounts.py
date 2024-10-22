# -*- coding: utf-8 -*-
#
from accounts.const import AutomationTypes
from accounts.models import AccountCheckAutomation
from common.utils import get_logger

from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = [
    'CheckAccountsAutomationSerializer',
]


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
