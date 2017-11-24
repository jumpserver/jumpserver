# ~*~ coding: utf-8 ~*~
import json

from django.contrib.auth.hashers import make_password, check_password
from django.db import models

from django.utils.translation import ugettext_lazy as _
from separatedvaluesfield.models import TextSeparatedValuesField
from assets.models import *
from collections import OrderedDict
from jsonfield import JSONField


class AnsibleRole(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))

    def __str__(self):
        return str(self.name)


class Task(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'), unique=True)
    desc = models.TextField(null=True, blank=True, verbose_name=_('Description'))
    password = models.CharField(max_length=200, verbose_name=_('WebHook Password'), blank=True, null=True)
    ansible_role = models.ForeignKey(AnsibleRole, verbose_name=_('Ansible Role'), related_name='task')
    tags = TextSeparatedValuesField(verbose_name=_('Tags'), null=True, blank=True)
    assets = models.ManyToManyField(Asset, verbose_name=_('Assets'), related_name='task', blank=True)
    groups = models.ManyToManyField(AssetGroup, verbose_name=_('Asset Groups'), related_name='task', blank=True)
    counts = models.IntegerField(default=0)
    system_user = models.ForeignKey(SystemUser, null=True, blank=True, verbose_name=_('System User'),
                                    related_name='task')

    def check_password(self, password_raw_):
        if self.password is None or self.password == "":
            return True
        else:
            return password_raw_ == self.password


class Record(models.Model):
    """Playbook Task 执行记录 """
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
    task = models.ForeignKey(Task, verbose_name=_('Task'), related_name='record', null=True, blank=True)

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


class Variable(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    desc = models.TextField(null=True, blank=True, verbose_name=_('Description'))
    vars = JSONField(null=True, blank=True, default={}, verbose_name=_('Vars'))
    assets = models.ManyToManyField(Asset, verbose_name=_('Assets'), related_name='variable', blank=True)
    groups = models.ManyToManyField(AssetGroup, verbose_name=_('Asset Groups'), related_name='variable', blank=True)
