# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ops.mixin import PeriodTaskSerializerMixin
from common.utils import get_logger
from common.const.choices import Trigger
from common.serializers.fields import LabeledChoiceField

from accounts.models import AccountBackupAutomation, AccountBackupExecution

logger = get_logger(__file__)

__all__ = ['AccountBackupSerializer', 'AccountBackupPlanExecutionSerializer']


class AccountBackupSerializer(PeriodTaskSerializerMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = AccountBackupAutomation
        read_only_fields = [
            'date_created', 'date_updated', 'created_by', 'periodic_display', 'executed_amount'
        ]
        fields = read_only_fields + [
            'id', 'name', 'is_periodic', 'interval', 'crontab', 'comment', 'recipients', 'types'
        ]
        extra_kwargs = {
            'name': {'required': True},
            'periodic_display': {'label': _('Periodic perform')},
            'executed_amount': {'label': _('Executed amount')},
            'recipients': {'label': _('Recipient'), 'help_text': _(
                'Currently only mail sending is supported'
            )}
        }


class AccountBackupPlanExecutionSerializer(serializers.ModelSerializer):
    trigger = LabeledChoiceField(choices=Trigger.choices, label=_("Trigger mode"), read_only=True)

    class Meta:
        model = AccountBackupExecution
        read_only_fields = [
            'id', 'date_start', 'timedelta', 'plan_snapshot', 'trigger', 'reason',
            'is_success', 'org_id', 'recipients'
        ]
        fields = read_only_fields + ['plan']
