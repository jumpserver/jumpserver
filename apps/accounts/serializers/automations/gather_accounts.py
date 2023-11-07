# -*- coding: utf-8 -*-
#
from accounts.const import AutomationTypes
from accounts.models import GatherAccountsAutomation
from common.utils import get_logger

from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = [
    'GatherAccountAutomationSerializer',
]


class GatherAccountAutomationSerializer(BaseAutomationSerializer):
    class Meta:
        model = GatherAccountsAutomation
        read_only_fields = BaseAutomationSerializer.Meta.read_only_fields
        fields = BaseAutomationSerializer.Meta.fields \
                 + ['is_sync_account', 'recipients'] + read_only_fields

        extra_kwargs = BaseAutomationSerializer.Meta.extra_kwargs

    @property
    def model_type(self):
        return AutomationTypes.gather_accounts
