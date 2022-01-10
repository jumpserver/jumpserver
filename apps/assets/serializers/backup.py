# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ops.mixin import PeriodTaskSerializerMixin
from common.utils import get_logger

from .base import TypesField

from ..models import AccountBackupPlan, AccountBackupPlanExecution

logger = get_logger(__file__)

__all__ = ['AccountBackupPlanSerializer', 'AccountBackupPlanExecutionSerializer']


class AccountBackupPlanSerializer(PeriodTaskSerializerMixin, BulkOrgResourceModelSerializer):
    types = TypesField(required=False, allow_null=True, label=_("Actions"))

    class Meta:
        model = AccountBackupPlan
        fields = [
            'id', 'name', 'is_periodic', 'interval', 'crontab', 'date_created',
            'date_updated', 'created_by', 'periodic_display', 'comment',
            'recipients', 'types'
        ]
        extra_kwargs = {
            'name': {'required': True},
            'periodic_display': {'label': _('Periodic perform')},
            'recipients': {'label': _('Recipient'), 'help_text': _(
                'Currently only mail sending is supported'
            )}
        }


class AccountBackupPlanExecutionSerializer(serializers.ModelSerializer):
    trigger_display = serializers.ReadOnlyField(
        source='get_trigger_display', label=_('Trigger mode')
    )

    class Meta:
        model = AccountBackupPlanExecution
        fields = [
            'id', 'date_start', 'timedelta', 'plan_snapshot', 'trigger', 'reason',
            'is_success', 'plan', 'org_id', 'recipients', 'trigger_display'
        ]
        read_only_fields = (
            'id', 'date_start', 'timedelta', 'plan_snapshot', 'trigger', 'reason',
            'is_success', 'org_id', 'recipients'
        )
