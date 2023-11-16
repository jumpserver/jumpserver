# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import AccountBackupAutomation, AccountBackupExecution
from common.const.choices import Trigger
from common.serializers.fields import LabeledChoiceField, EncryptedField
from common.utils import get_logger
from ops.mixin import PeriodTaskSerializerMixin
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

logger = get_logger(__file__)

__all__ = ['AccountBackupSerializer', 'AccountBackupPlanExecutionSerializer']


class AccountBackupSerializer(PeriodTaskSerializerMixin, BulkOrgResourceModelSerializer):
    zip_encrypt_password = EncryptedField(
        label=_('Zip Encrypt Password'), required=False, max_length=40960, allow_blank=True,
        allow_null=True, write_only=True,
    )

    class Meta:
        model = AccountBackupAutomation
        read_only_fields = [
            'date_created', 'date_updated', 'created_by',
            'periodic_display', 'executed_amount'
        ]
        fields = read_only_fields + [
            'id', 'name', 'is_periodic', 'interval', 'crontab',
            'comment', 'types', 'recipients_part_one', 'recipients_part_two', 'backup_type',
            'is_password_divided_by_email', 'is_password_divided_by_obj_storage', 'obj_recipients_part_one',
            'obj_recipients_part_two', 'zip_encrypt_password'
        ]
        extra_kwargs = {
            'name': {'required': True},
            'periodic_display': {'label': _('Periodic perform')},
            'executed_amount': {'label': _('Executed amount')},
            'recipients': {
                'label': _('Recipient'),
                'help_text': _('Currently only mail sending is supported')
            },
            'types': {'label': _('Asset type')}
        }


class AccountBackupPlanExecutionSerializer(serializers.ModelSerializer):
    trigger = LabeledChoiceField(choices=Trigger.choices, label=_("Trigger mode"), read_only=True)

    class Meta:
        model = AccountBackupExecution
        read_only_fields = [
            'id', 'date_start', 'timedelta', 'snapshot',
            'trigger', 'reason', 'is_success', 'org_id'
        ]
        fields = read_only_fields + ['plan']
