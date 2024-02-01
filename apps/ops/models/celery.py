# -*- coding: utf-8 -*-
#
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from ops.celery import app


class CeleryTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=1024, verbose_name=_('Name'))
    date_last_publish = models.DateTimeField(null=True, verbose_name=_("Date last publish"))

    @property
    def meta(self):
        task = app.tasks.get(self.name, None)
        return {
            "comment": getattr(task, 'verbose_name', None),
            "queue": getattr(task, 'queue', 'default')
        }

    @property
    def summary(self):
        executions = CeleryTaskExecution.objects.filter(name=self.name)
        total = executions.count()
        success = executions.filter(state='SUCCESS').count()
        return {'total': total, 'success': success}

    @property
    def state(self):
        last_five_executions = CeleryTaskExecution.objects \
                                   .filter(name=self.name) \
                                   .order_by('-date_published')[:5]

        if len(last_five_executions) > 0:
            if last_five_executions[0].state == 'FAILURE':
                return "red"

        for execution in last_five_executions:
            if execution.state == 'FAILURE':
                return "yellow"
        return "green"

    class Meta:
        verbose_name = _("Celery Task")
        ordering = ('name',)
        permissions = [
            ('view_taskmonitor', _('Can view task monitor'))
        ]


class CeleryTaskExecution(models.Model):
    LOG_DIR = os.path.join(settings.PROJECT_DIR, 'data', 'celery')
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=1024, verbose_name=_('Name'))
    args = models.JSONField(verbose_name=_("Args"))
    kwargs = models.JSONField(verbose_name=_("Kwargs"))
    state = models.CharField(max_length=16, verbose_name=_("State"))
    is_finished = models.BooleanField(default=False, verbose_name=_("Finished"))
    date_published = models.DateTimeField(auto_now_add=True, verbose_name=_('Date published'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'))
    date_finished = models.DateTimeField(null=True, verbose_name=_('Date finished'))

    @property
    def time_cost(self):
        if self.date_finished and self.date_start:
            return (self.date_finished - self.date_start).total_seconds()
        return None

    @property
    def timedelta(self):
        if self.date_start and self.date_finished:
            return self.date_finished - self.date_start
        return None

    @property
    def is_success(self):
        return self.state == 'SUCCESS'

    def __str__(self):
        return "{}: {}".format(self.name, self.id)

    class Meta:
        ordering = ['-date_start']
        verbose_name = _("Celery Task Execution")
