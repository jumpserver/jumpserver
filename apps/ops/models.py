# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging
from collections import OrderedDict
import json

from django.db import models
from django.utils.translation import ugettext_lazy as _
from assets.models import Asset

__all__ = ["Task"]


logger = logging.getLogger(__name__)


class Task(models.Model):
    uuid = models.CharField(max_length=128, verbose_name=_('UUID'), primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    assets = models.TextField(blank=True, null=True, verbose_name=_('Assets id'))  # Asset inventory may be change
    _modules_args = models.TextField(blank=True, null=True, verbose_name=_('Task module and args json format'))
    pattern = models.CharField(max_length=64, default='all', verbose_name=_('Task run pattern'))
    result = models.TextField(blank=True, null=True, verbose_name=_('Task raw result'))
    summary = models.TextField(blank=True, null=True, verbose_name=_('Task summary'))

    def __unicode__(self):
        return "%s" % self.uuid

    @property
    def total_assets(self):
        assets_id = [i for i in self.assets.split(',') if i.isdigit()]
        assets = Asset.objects.filter(id__in=assets_id)
        return assets

    @property
    def assets_json(self):
        return [asset._to_secret_json() for asset in self.total_assets]

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


