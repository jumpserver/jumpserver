# -*- coding: utf-8 -*-
#
import abc
import uuid
from django.utils.translation import ugettext_lazy as _

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .celery.utils import (
    create_or_update_celery_periodic_tasks, disable_celery_periodic_task,
    delete_celery_periodic_task,
)

__all__ = ['PeriodTaskMixin']


class PeriodTaskMixin(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(
        max_length=128, unique=False, verbose_name=_("Name")
    )
    is_periodic = models.BooleanField(default=False)
    interval = models.IntegerField(
        default=24, null=True, blank=True, verbose_name=_("Cycle perform"),
    )
    crontab = models.CharField(
        null=True, blank=True, max_length=128,
        verbose_name=_("Regularly perform"),
    )

    @abc.abstractmethod
    def get_register_task(self):
        period_name, task, args, kwargs = None, None, (), {}
        return period_name, task, args, kwargs

    @property
    def interval_ratio(self):
        return 3600, 'h'

    @property
    def interval_display(self):
        unit = self.interval_ratio[1]
        if not self.interval:
            return ''
        return '{} {}'.format(self.interval, unit)

    def set_period_schedule(self):
        name, task, args, kwargs = self.get_register_task()
        if not self.is_periodic:
            disable_celery_periodic_task(name)
            return

        crontab = interval = None
        if self.crontab:
            crontab = self.crontab
        elif self.interval:
            interval = self.interval * self.interval_ratio[0]

        tasks = {
            name: {
                'task': task,
                'interval': interval,
                'crontab': crontab,
                'args': args,
                'kwargs': kwargs,
                'enabled': True,
            }
        }
        create_or_update_celery_periodic_tasks(tasks)

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        return instance

    def delete(self, using=None, keep_parents=False):
        name = self.get_register_task()[0]
        instance = super().delete(using=using, keep_parents=keep_parents)
        delete_celery_periodic_task(name)
        return instance

    @property
    def schedule(self):
        from django_celery_beat.models import PeriodicTask
        try:
            return PeriodicTask.objects.get(name=str(self))
        except PeriodicTask.DoesNotExist:
            return None

    class Meta:
        abstract = True
