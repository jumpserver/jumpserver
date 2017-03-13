# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging
from collections import OrderedDict
import json

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ["TaskRecord"]


logger = logging.getLogger(__name__)


class TaskRecord(models.Model):
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'), primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    assets = models.TextField(blank=True, null=True, verbose_name=_('Assets for hostname'))  # Asset inventory may be change
    _modules_args = models.TextField(blank=True, null=True, verbose_name=_('Task module and args json format'))
    pattern = models.CharField(max_length=64, default='all', verbose_name=_('Task run pattern'))
    result = models.TextField(blank=True, null=True, verbose_name=_('Task raw result'))
    summary = models.TextField(blank=True, null=True, verbose_name=_('Task summary'))

    def __unicode__(self):
        return "%s" % self.uuid

    @property
    def total_assets(self):
        return self.assets.split(',')

    @property
    def assets_json(self):
        from assets.models import Asset
        return [Asset.objects.get(hostname=hostname)._to_secret_json()
                for hostname in self.total_assets
                if Asset.objects.exists(hostname=hostname)]

    @property
    def module_args(self):
        task_tuple = []
        for module, args in json.loads(self._modules_args, object_pairs_hook=OrderedDict).items():
            task_tuple.append((module, args))
        return task_tuple

    @module_args.setter
    def module_args(self, task_tuple):
        module_args_ = OrderedDict({})
        for module, args in task_tuple:
            module_args_[module] = args
        self._modules_args = json.dumps(module_args_)


