# ~*~ coding: utf-8 ~*~

import logging
from collections import OrderedDict
import json
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ["Playbook"]


logger = logging.getLogger(__name__)


class AdHoc(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    tasks = models.TextField(verbose_name=_('Tasks'))  # [{'name': 'task_name', 'module': '', 'args': ''}, ]
    hosts = models.TextField(blank=True, null=True, verbose_name=_('Hosts'))  # Asset inventory may be change
    pattern = models.CharField(max_length=64, default='all', verbose_name=_('Playbook run pattern'))

    def __str__(self):
        return "%s" % self.name

    def get_hosts_mapped_assets(self):
        from assets.utils import get_assets_by_id_list
        assets_id = [i for i in self.hosts.split(',')]
        assets = get_assets_by_id_list(assets_id)
        return assets

    @property
    def inventory(self):
        return [asset._to_secret_json() for asset in self.get_hosts_mapped_assets()]

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


class History(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    result = models.TextField(blank=True, null=True, verbose_name=_('Playbook raw result'))
    summary = models.TextField(blank=True, null=True, verbose_name=_('Playbook summary'))
