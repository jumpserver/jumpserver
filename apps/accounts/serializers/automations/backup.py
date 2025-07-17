# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes, AccountBackupType
from accounts.models import BackupAccountAutomation
from common.serializers.fields import EncryptedField
from common.utils import get_logger
from .base import BaseAutomationSerializer

logger = get_logger(__file__)

__all__ = ['BackupAccountSerializer']


class BackupAccountSerializer(BaseAutomationSerializer):
    zip_encrypt_password = EncryptedField(
        label=_('Zip Encrypt Password'), required=False, max_length=40960, allow_blank=True,
        allow_null=True, write_only=True,
    )

    class Meta:
        model = BackupAccountAutomation
        read_only_fields = BaseAutomationSerializer.Meta.read_only_fields
        fields = BaseAutomationSerializer.Meta.fields + read_only_fields + [
            'types', 'recipients_part_one', 'recipients_part_two', 'backup_type',
            'is_password_divided_by_email', 'is_password_divided_by_obj_storage',
            'obj_recipients_part_one', 'obj_recipients_part_two', 'zip_encrypt_password'
        ]
        extra_kwargs = {
            **BaseAutomationSerializer.Meta.extra_kwargs,
            'name': {'required': True},
            'obj_recipients_part_one': {
                'label': _('Recipient part one'), 'help_text': _(
                    "Currently only mail sending is supported"
                )},
            'obj_recipients_part_two': {
                'label': _('Recipient part two'), 'help_text': _(
                    "Currently only mail sending is supported"
                )},
            'types': {'label': _('Asset type')}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_backup_type_choices()

    def set_backup_type_choices(self):
        field_backup_type = self.fields.get("backup_type")
        if not field_backup_type:
            return
        if not settings.XPACK_LICENSE_IS_VALID:
            field_backup_type._choices.pop(AccountBackupType.object_storage, None)

    @property
    def model_type(self):
        return AutomationTypes.backup_account
