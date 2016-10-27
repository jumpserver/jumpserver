# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger(__name__)


class Play(models.Model):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'))
    completed = models.BooleanField(default=False, verbose_name=_('IsCompleted'))
    status_code = models.IntegerField(default=0, verbose_name=_('StatusCode'))

    def __unicode__(self):
        return self.name


class Task(models.Model):
    play = models.ForeignKey(Play, related_name='tasks', blank=True)
    name = models.CharField(max_length=128, blank=True, blverbose_name=_('Name'))
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'))

    def __unicode__(self):
        return self.clean()


class HostResult(models.Model):
    task = models.ForeignKey(Task, related_name='host_results', blank=True)

