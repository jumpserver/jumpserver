# -*- coding: utf-8 -*-
#
import abc
from datetime import timedelta

from celery.schedules import crontab
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, ClockedSchedule
from rest_framework import serializers

from .celery.utils import (
    create_or_update_celery_periodic_tasks, disable_celery_periodic_task,
    delete_celery_periodic_task,
)

__all__ = [
    'PeriodTaskModelMixin', 'PeriodTaskSerializerMixin',
]


class PeriodTaskModelQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        for obj in self:
            obj.delete()
        return super().delete(*args, **kwargs)


class PeriodTaskModelMixin(models.Model):
    name = models.CharField(
        max_length=128, unique=False, verbose_name=_("Name")
    )
    is_periodic = models.BooleanField(default=False, verbose_name=_("Periodic run"))
    interval = models.IntegerField(
        default=24, null=True, blank=True, verbose_name=_("Interval"),
    )
    crontab = models.CharField(
        blank=True, max_length=128, default='', verbose_name=_("Crontab"),
    )
    start_time = models.DateTimeField(
        blank=True, null=True,
        verbose_name=_('Start Datetime'),
        help_text=_(
            'Datetime when the schedule should begin '
            'triggering the task to run'
        ),
    )
    date_last_run = models.DateTimeField(blank=True, null=True, verbose_name=_("Date last run"))
    objects = PeriodTaskModelQuerySet.as_manager()

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
        is_active = self.is_active if hasattr(self, 'is_active') else True
        if not self.is_periodic or not is_active:
            disable_celery_periodic_task(name)
            return

        cron = interval = None
        if self.crontab:
            cron = self.crontab
        elif self.interval:
            interval = self.interval * self.interval_ratio[0]

        tasks = {
            name: {
                'task': task,
                'interval': interval,
                'crontab': cron,
                'args': args,
                'kwargs': kwargs,
                'enabled': True,
                'start_time': self.start_time,
            }
        }
        create_or_update_celery_periodic_tasks(tasks)

    def execute(self, *args, **kwargs):
        self.date_last_run = timezone.now()

    def save(self, *args, **kwargs):
        instance = super().save(**kwargs)
        self.set_period_schedule()
        return instance

    def delete(self, using=None, keep_parents=False):
        name = self.get_register_task()[0]
        instance = super().delete(using=using, keep_parents=keep_parents)
        delete_celery_periodic_task(name)
        return instance

    @property
    def periodic_display(self):
        if self.is_periodic and self.crontab:
            return _('Crontab') + " ( {} )".format(self.crontab)
        if self.is_periodic and self.interval:
            return _('Interval') + " ( {} h )".format(self.interval)
        return '-'

    @property
    def schedule(self):
        from django_celery_beat.models import PeriodicTask
        name = self.get_register_task()[0]
        return PeriodicTask.objects.filter(name=name).first()

    def get_next_run_time(self):
        if not self.is_periodic:
            return None
        task = self.schedule
        now = task.schedule.nowfun()

        if self.start_time and self.start_time > now:
            return self.start_time

        scheduler = task.scheduler
        # 根据不同的调度类型计算下次执行时间
        if isinstance(scheduler, CrontabSchedule):
            schedule = crontab(
                minute=scheduler.minute,
                hour=scheduler.hour,
                day_of_week=scheduler.day_of_week,
                day_of_month=scheduler.day_of_month,
                month_of_year=scheduler.month_of_year,
            )
            next_run = schedule.remaining_estimate(now)
            return now + next_run
        elif isinstance(scheduler, IntervalSchedule):
            interval = timedelta(
                seconds=scheduler.every * {
                    IntervalSchedule.SECONDS: 1,
                    IntervalSchedule.MINUTES: 60,
                    IntervalSchedule.HOURS: 3600,
                    IntervalSchedule.DAYS: 86400,
                }[scheduler.period]
            )
            last_run = task.last_run_at or now
            return last_run + interval

        elif isinstance(scheduler, ClockedSchedule):
            return scheduler.clocked_time

        else:
            raise ValueError("不支持的任务调度类型")

    class Meta:
        abstract = True


class PeriodTaskSerializerMixin(serializers.Serializer):
    is_periodic = serializers.BooleanField(default=True, label=_("Periodic run"))
    crontab = serializers.CharField(
        max_length=128, allow_blank=True,
        allow_null=True, required=False, label=_('Crontab')
    )
    interval = serializers.IntegerField(
        default=24, allow_null=True, required=False, label=_('Interval'),
        max_value=65535, min_value=1,
    )
    start_time = serializers.DateTimeField(
        allow_null=True, required=False,
        label=_('Start Datetime'),
        help_text=_(
            'Datetime when the schedule should begin '
            'triggering the task to run'
        ),
    )
    periodic_display = serializers.CharField(read_only=True, label=_('Run period'))

    def validate_crontab(self, crontab):
        if not crontab:
            return crontab
        if isinstance(crontab, str) and len(crontab.strip().split()) != 5:
            msg = _('* Please enter a valid crontab expression')
            raise serializers.ValidationError(msg)
        return crontab

    def validate_interval(self, interval):
        if not interval and not isinstance(interval, int):
            return interval
        return interval

    def validate_is_periodic(self, ok):
        if not ok:
            return ok
        crontab = self.initial_data.get('crontab')
        interval = self.initial_data.get('interval')
        if ok and not any([crontab, interval]):
            msg = _("Require interval or crontab setting")
            raise serializers.ValidationError(msg)
        return ok

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get('is_periodic'):
            attrs['interval'] = None
            attrs['crontab'] = ''
        if attrs.get('crontab'):
            attrs['interval'] = None
        return attrs
