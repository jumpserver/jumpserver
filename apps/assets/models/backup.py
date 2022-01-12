#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import uuid

from celery import current_task
from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin
from ops.mixin import PeriodTaskModelMixin
from common.utils import get_logger
from common.db.encoder import ModelJSONFieldEncoder
from common.db.models import BitOperationChoice
from common.mixins.models import CommonModelMixin

__all__ = ['AccountBackupPlan', 'AccountBackupPlanExecution', 'Type']

logger = get_logger(__file__)


class Type(BitOperationChoice):
    NONE = 0
    ALL = 0xff

    Asset = 0b1
    App = 0b1 << 1

    DB_CHOICES = (
        (ALL, _('All')),
        (Asset, _('Asset')),
        (App, _('Application'))
    )

    NAME_MAP = {
        ALL: "all",
        Asset: "asset",
        App: "application"
    }

    NAME_MAP_REVERSE = {v: k for k, v in NAME_MAP.items()}
    CHOICES = []
    for i, j in DB_CHOICES:
        CHOICES.append((NAME_MAP[i], j))


class AccountBackupPlan(CommonModelMixin, PeriodTaskModelMixin, OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    types = models.IntegerField(choices=Type.DB_CHOICES, default=Type.ALL, verbose_name=_('Type'))
    recipients = models.ManyToManyField(
        'users.User', related_name='recipient_escape_route_plans', blank=True,
        verbose_name=_("Recipient")
    )
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return f'{self.name}({self.org_id})'

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _('Account backup plan')

    def get_register_task(self):
        from ..tasks import execute_account_backup_plan
        name = "account_backup_plan_period_{}".format(str(self.id)[:8])
        task = execute_account_backup_plan.name
        args = (str(self.id), AccountBackupPlanExecution.Trigger.timing)
        kwargs = {}
        return name, task, args, kwargs

    def to_attr_json(self):
        return {
            'name': self.name,
            'is_periodic': self.is_periodic,
            'interval': self.interval,
            'crontab': self.crontab,
            'org_id': self.org_id,
            'created_by': self.created_by,
            'types': Type.value_to_choices(self.types),
            'recipients': {
                str(recipient.id): (str(recipient), bool(recipient.secret_key))
                for recipient in self.recipients.all()
            }
        }

    def execute(self, trigger):
        try:
            hid = current_task.request.id
        except AttributeError:
            hid = str(uuid.uuid4())
        execution = AccountBackupPlanExecution.objects.create(
            id=hid, plan=self, plan_snapshot=self.to_attr_json(), trigger=trigger
        )
        return execution.start()


class AccountBackupPlanExecution(OrgModelMixin):
    class Trigger(models.TextChoices):
        manual = 'manual', _('Manual trigger')
        timing = 'timing', _('Timing trigger')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    date_start = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date start')
    )
    timedelta = models.FloatField(
        default=0.0, verbose_name=_('Time'), null=True
    )
    plan_snapshot = models.JSONField(
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
        'AccountBackupPlan', related_name='execution', on_delete=models.CASCADE,
        verbose_name=_('Account backup plan')
    )

    class Meta:
        verbose_name = _('Account backup execution')

    @property
    def types(self):
        types = self.plan_snapshot.get('types')
        return types

    @property
    def recipients(self):
        recipients = self.plan_snapshot.get('recipients')
        if not recipients:
            return []
        return recipients.values()

    def start(self):
        from ..task_handlers import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager.run()
