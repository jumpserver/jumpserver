# ~*~ coding: utf-8 ~*~

import logging
import json
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ["AdHoc", "History"]


logger = logging.getLogger(__name__)


class AdHoc(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    def __str__(self):
        return self.name


class AdHocData(models.Model):
    BECOME_METHOD_CHOICES = (
        ('sudo', 'sudo'),
        ('su', 'su'),
    )
    version = models.UUIDField(default=uuid.uuid4, primary_key=True)
    subject = models.ForeignKey(AdHoc, on_delete=models.CASCADE)
    _tasks = models.TextField(verbose_name=_('Tasks'))  # [{'name': 'task_name', 'action': {'module': '', 'args': ''}, 'other..': ''}, ]
    _hosts = models.TextField(blank=True, verbose_name=_('Hosts'))  # ['hostname1', 'hostname2']
    run_as_admin = models.BooleanField(default=False, verbose_name=_('Run as admin'))
    run_as = models.CharField(max_length=128, verbose_name=_("Run as"))
    become = models.BooleanField(default=False, verbose_name=_("Become"))
    become_method = models.CharField(choices=BECOME_METHOD_CHOICES, default='sudo', max_length=4)
    become_user = models.CharField(default='root', max_length=64)
    become_pass = models.CharField(default='', max_length=128)
    pattern = models.CharField(max_length=64, default='', verbose_name=_('Pattern'))
    created_by = models.CharField(max_length=64, verbose_name=_('Create by'))
    date_created = models.DateTimeField(auto_created=True)

    @property
    def tasks(self):
        return json.loads(self._tasks)

    @tasks.setter
    def tasks(self, item):
        self._tasks = json.dumps(item)

    @property
    def hosts(self):
        return json.loads(self._hosts)

    @hosts.setter
    def hosts(self, item):
        self._hosts = json.dumps(item)

    @property
    def short_version(self):
        return str(self.version).split('-')[-1]

    def __str__(self):
        return "{} of {}".format(self.subject.name, self.short_version)


class AdHocHistory(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, primary_key=True)
    adhoc = models.ForeignKey(AdHocData, on_delete=models.CASCADE)
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    result = models.TextField(blank=True, null=True, verbose_name=_('Playbook raw result'))
    summary = models.TextField(blank=True, null=True, verbose_name=_('Playbook summary'))

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    def __str__(self):
        return self.short_id
