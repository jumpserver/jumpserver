# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ["TaskRecord"]


logger = logging.getLogger(__name__)


class TaskRecord(models.Model):
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'), primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    assets = models.TextField(blank=True, null=True, verbose_name=_('Assets'))
    result = models.TextField(blank=True, null=True, verbose_name=_('Task result'))

    def __unicode__(self):
        return "%s" % self.uuid

    @property
    def total_assets(self):
        return self.assets.split(',')

