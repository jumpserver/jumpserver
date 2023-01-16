# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
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
        fields = BaseAutomationSerializer.Meta.fields + read_only_fields

        extra_kwargs = BaseAutomationSerializer.Meta.extra_kwargs
