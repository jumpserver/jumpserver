#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import uuid

from celery import current_task
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from accounts.const.automation import AccountBackupType
from common.const.choices import Trigger
from common.db import fields
from common.db.encoder import ModelJSONFieldEncoder
from common.utils import get_logger, lazyproperty
from ops.mixin import PeriodTaskModelMixin
from orgs.mixins.models import OrgModelMixin, JMSOrgBaseModel

__all__ = ['AccountBackupAutomation', 'AccountBackupExecution']

logger = get_logger(__file__)


class AccountBackupAutomation(PeriodTaskModelMixin, JMSOrgBaseModel):
    types = models.JSONField(default=list)
    backup_type = models.CharField(max_length=128, choices=AccountBackupType.choices,
                                   default=AccountBackupType.email.value, verbose_name=_('Backup Type'))
    is_password_divided_by_email = models.BooleanField(default=True, verbose_name=_('Is Password Divided'))
    is_password_divided_by_obj_storage = models.BooleanField(default=True, verbose_name=_('Is Password Divided'))
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
        verbose_name=_("Object Storage Recipient part one")
    )
    obj_recipients_part_two = models.ManyToManyField(
        'terminal.ReplayStorage', related_name='obj_recipient_part_two_plans', blank=True,
        verbose_name=_("Object Storage Recipient part two")
    )
    zip_encrypt_password = fields.EncryptCharField(max_length=4096, blank=True, null=True,
                                                   verbose_name=_('Zip Encrypt Password'))

    def __str__(self):
        return f'{self.name}({self.org_id})'

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _('Account backup plan')

    def get_register_task(self):
        from ...tasks import execute_account_backup_task
        name = "account_backup_plan_period_{}".format(str(self.id)[:8])
        task = execute_account_backup_task.name
        args = (str(self.id), Trigger.timing)
        kwargs = {}
        return name, task, args, kwargs

    def to_attr_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'is_periodic': self.is_periodic,
            'interval': self.interval,
            'crontab': self.crontab,
            'org_id': self.org_id,
            'created_by': self.created_by,
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
        }

    @property
    def executed_amount(self):
        return self.execution.count()

    def execute(self, trigger):
        try:
            hid = current_task.request.id
        except AttributeError:
            hid = str(uuid.uuid4())
        execution = AccountBackupExecution.objects.create(
            id=hid, plan=self, snapshot=self.to_attr_json(), trigger=trigger
        )
        return execution.start()

    @lazyproperty
    def latest_execution(self):
        return self.execution.first()


class AccountBackupExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    date_start = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date start')
    )
    timedelta = models.FloatField(
        default=0.0, verbose_name=_('Time'), null=True
    )
    snapshot = models.JSONField(
        encoder=ModelJSONFieldEncoder, default=dict,
        blank=True, null=True, verbose_name=_('Account backup snapshot')
    )
    trigger = models.CharField(
        max_length=128, default=Trigger.manual, choices=Trigger.choices,
        verbose_name=_('Trigger mode')
    )
    reason = models.CharField(
        max_length=1024, blank=True, null=True, verbose_name=_('Reason')
    )
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    plan = models.ForeignKey(
        'AccountBackupAutomation', related_name='execution', on_delete=models.CASCADE,
        verbose_name=_('Account backup plan')
    )

    class Meta:
        ordering = ('-date_start',)
        verbose_name = _('Account backup execution')

    @property
    def types(self):
        types = self.snapshot.get('types')
        return types

    @lazyproperty
    def backup_accounts(self):
        from accounts.models import Account
        # TODO 可以优化一下查询 在账号上做 category 的缓存 避免数据量大时连表操作
        qs = Account.objects.filter(
            asset__platform__type__in=self.types
        ).annotate(type=F('asset__platform__type'))
        return qs

    @property
    def manager_type(self):
        return 'backup_account'

    def start(self):
        from accounts.automations.endpoint import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager.run()
