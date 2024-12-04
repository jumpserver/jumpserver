#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.const import AccountBackupType, AutomationTypes
from common.db import fields
from common.utils import get_logger
from .base import AccountBaseAutomation

__all__ = ['BackupAccountAutomation']

logger = get_logger(__file__)


class BackupAccountAutomation(AccountBaseAutomation):
    types = models.JSONField(default=list)
    backup_type = models.CharField(
        max_length=128, choices=AccountBackupType.choices,
        default=AccountBackupType.email, verbose_name=_('Backup type')
    )
    is_password_divided_by_email = models.BooleanField(default=True, verbose_name=_('Password divided'))
    is_password_divided_by_obj_storage = models.BooleanField(default=True, verbose_name=_('Password divided'))
    recipients_part_one = models.ManyToManyField(
        'users.User', related_name='recipient_part_one_plans', blank=True,
        verbose_name=_("Recipient part one")
    )
    recipients_part_two = models.ManyToManyField(
        'users.User', related_name='recipient_part_two_plans', blank=True,
        verbose_name=_("Recipient part two")
    )
    obj_recipients_part_one = models.ManyToManyField(
        'terminal.ReplayStorage', related_name='obj_recipient_part_one_plans', blank=True,
        verbose_name=_("Object storage recipient part one")
    )
    obj_recipients_part_two = models.ManyToManyField(
        'terminal.ReplayStorage', related_name='obj_recipient_part_two_plans', blank=True,
        verbose_name=_("Object storage recipient part two")
    )
    zip_encrypt_password = fields.EncryptCharField(
        max_length=4096, blank=True, null=True, verbose_name=_('Zip encrypt password')
    )

    def __str__(self):
        return f'{self.name}({self.org_id})'

    class Meta:
        verbose_name = _('Account backup plan')

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'types': self.types,
            'backup_type': self.backup_type,
            'is_password_divided_by_email': self.is_password_divided_by_email,
            'is_password_divided_by_obj_storage': self.is_password_divided_by_obj_storage,
            'zip_encrypt_password': self.zip_encrypt_password,
            'recipients_part_one': {
                str(user.id): (str(user), bool(user.secret_key))
                for user in self.recipients_part_one.all()
            },
            'recipients_part_two': {
                str(user.id): (str(user), bool(user.secret_key))
                for user in self.recipients_part_two.all()
            },
            'obj_recipients_part_one': {
                str(obj_storage.id): (str(obj_storage.name), str(obj_storage.type))
                for obj_storage in self.obj_recipients_part_one.all()
            },
            'obj_recipients_part_two': {
                str(obj_storage.id): (str(obj_storage.name), str(obj_storage.type))
                for obj_storage in self.obj_recipients_part_two.all()
            },
        })
        return attr_json

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.backup_account
        super().save(*args, **kwargs)
