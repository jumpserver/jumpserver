# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging

from uuid import uuid4
from assets.models import Asset
from ops.models import TaskRecord

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ["Task", "SubTask"]


logger = logging.getLogger(__name__)


class Task(models.Model):
    record = models.OneToOneField(TaskRecord)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    is_gather_facts = models.BooleanField(default=False, verbose_name=_('Is Gather Ansible Facts'))
    assets = models.ManyToManyField(Asset, related_name='tasks')

    def __unicode__(self):
        return "%s" % self.name

    @property
    def ansible_assets(self):
        return []

    def run(self):
        from ops.utils.ansible_api import ADHocRunner, Options
        conf = Options()
        gather_facts = "yes" if self.is_gather_facts else "no"
        play_source = {
            "name": "Ansible Play",
            "hosts": "default",
            "gather_facts": gather_facts,
            "tasks": [
                dict(action=dict(module='ping')),
            ]
        }
        hoc = ADHocRunner(conf, play_source, *self.ansible_assets)
        uuid = "tasker-" + uuid4().hex
        ext_code, result = hoc.run("test_task", uuid)
        print(ext_code)
        print(result)


class SubTask(models.Model):
    task = models.ForeignKey(Task, related_name='sub_tasks', verbose_name=_('Ansible Task'))
    module_name = models.CharField(max_length=128, verbose_name=_('Ansible Module Name'))
    module_args = models.CharField(max_length=512, blank=True, verbose_name=_("Ansible Module Args"))
    register = models.CharField(max_length=128, blank=True, verbose_name=_('Ansible Task Register'))

    def __unicode__(self):
        return "%s %s" % (self.module_name, self.module_args)
