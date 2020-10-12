# -*- coding: utf-8 -*-
#
import abc
import uuid
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django import forms
from rest_framework import serializers

from .celery.utils import (
    create_or_update_celery_periodic_tasks, disable_celery_periodic_task,
    delete_celery_periodic_task,
)

__all__ = [
    'PeriodTaskModelMixin', 'PeriodTaskSerializerMixin',
    'PeriodTaskFormMixin',
]


class PeriodTaskModelMixin(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(
        max_length=128, unique=False, verbose_name=_("Name")
    )
    is_periodic = models.BooleanField(default=False)
    interval = models.IntegerField(
        default=24, null=True, blank=True,
        verbose_name=_("Cycle perform"),
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
            return _('Regularly perform') + " ( {} )".format(self.crontab)
        if self.is_periodic and self.interval:
            return _('Cycle perform') + " ( {} h )".format(self.interval)
        return '-'

    @property
    def schedule(self):
        from django_celery_beat.models import PeriodicTask
        name = self.get_register_task()[0]
        return PeriodicTask.objects.filter(name=name).first()

    class Meta:
        abstract = True


class PeriodTaskSerializerMixin(serializers.Serializer):
    is_periodic = serializers.BooleanField(default=False, label=_("Periodic perform"))
    crontab = serializers.CharField(
        max_length=128, allow_blank=True,
        allow_null=True, required=False, label=_('Regularly perform')
    )
    interval = serializers.IntegerField(allow_null=True, required=False, label=_('Interval'))

    INTERVAL_MAX = 65535
    INTERVAL_MIN = 1

    def validate_crontab(self, crontab):
        if not crontab:
            return crontab
        if isinstance(crontab, str) and len(crontab.strip().split()) != 5:
            msg = _('* Please enter a valid crontab expression')
            raise serializers.ValidationError(msg)
        return crontab

    def validate_interval(self, interval):
        if not interval:
            return interval
        msg = _("Range {} to {}").format(self.INTERVAL_MIN, self.INTERVAL_MAX)
        if interval > self.INTERVAL_MAX or interval < self.INTERVAL_MIN:
            raise serializers.ValidationError(msg)
        return interval

    def validate_is_periodic(self, ok):
        if not ok:
            return ok
        crontab = self.initial_data.get('crontab')
        interval = self.initial_data.get('interval')
        if ok and not any([crontab, interval]):
            msg = _("Require periodic or regularly perform setting")
            raise serializers.ValidationError(msg)
        return ok


class PeriodTaskFormMixin(forms.Form):
    is_periodic = forms.BooleanField(
        initial=True, required=False, label=_('Periodic perform')
    )
    crontab = forms.CharField(
        max_length=128, required=False, label=_('Regularly perform'),
        help_text=_("eg: Every Sunday 03:05 run <5 3 * * 0> <br> "
                    "Tips: "
                    "Using 5 digits linux crontab expressions "
                    "<min hour day month week> "
                    "(<a href='https://tool.lu/crontab/' target='_blank'>Online tools</a>) <br>"
                    "Note: "
                    "If both Regularly perform and Cycle perform are set, "
                    "give priority to Regularly perform"),
    )
    interval = forms.IntegerField(
        required=False, initial=24,
        help_text=_('Tips: (Units: hour)'), label=_("Cycle perform"),
    )

    def get_initial_for_field(self, field, field_name):
        """
        Return initial data for field on form. Use initial data from the form
        or the field, in that order. Evaluate callable values.
        """
        if field_name not in ['is_periodic', 'crontab', 'interval']:
            return super().get_initial_for_field(field, field_name)
        instance = getattr(self, 'instance', None)
        if instance is None:
            return super().get_initial_for_field(field, field_name)
        init_attr_name = field_name + '_initial'
        value = getattr(self, init_attr_name, None)
        if value is None:
            return super().get_initial_for_field(field, field_name)
        return value


