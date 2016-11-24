# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

from django.db import models
from assets.models import Asset
from django.utils.translation import ugettext_lazy as _


class CronTable(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, unique=True, verbose_name=_('Name'),
                            help_text=_("Description of a crontab entry"))
    month = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Month'),
                             help_text=_("Month of the year the job should run ( 1-12, *, */2, etc )"))
    weekday = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('WeekDay'),
                               help_text=_("Day of the week that the job should run"
                                           " ( 0-6 for Sunday-Saturday, *, etc )"))
    day = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Day'),
                           help_text=_("Day of the month the job should run ( 1-31, *, */2, etc )"))
    hour = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Hour'),
                            help_text=_("Hour when the job should run ( 0-23, *, */2, etc )"))
    minute = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Minute'),
                              help_text=_("Minute when the job should run ( 0-59, *, */2, etc )"))
    job = models.CharField(max_length=4096, blank=True, null=True, verbose_name=_('Job'),
                           help_text=_("The command to execute or, if env is set, the value of "
                                       "environment variable. Required if state=present."))
    user = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('User'),
                            help_text=_("The specific user whose crontab should be modified."))
    asset = models.ForeignKey(Asset, null=True, blank=True, related_name='crontables')

    @property
    def describe(self):
        return "http://docs.ansible.com/ansible/cron_module.html"