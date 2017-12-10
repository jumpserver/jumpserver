# ~*~ coding: utf-8 ~*~

import logging
import json
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import signer

__all__ = ["Task", "AdHoc", "AdHocRunHistory"]


logger = logging.getLogger(__name__)


class Task(models.Model):
    """
    This task is different ansible task, Task like 'push system user', 'get asset info' ..
    One task can have some versions of adhoc, run a task only run the latest version adhoc
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, blank=True, verbose_name=_('Name'))
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=128, blank=True, default='')
    date_created = models.DateTimeField(auto_now_add=True)

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    def __str__(self):
        return self.name

    def get_latest_adhoc(self):
        return self.adhoc.all().order_by('date_created').last()

    def get_latest_history(self):
        return self.get_latest_adhoc().get_latest_history()

    def get_all_run_history(self):
        adhocs = self.adhoc.all()
        return AdHocRunHistory.objects.filter(adhoc__in=adhocs)

    def get_all_run_times(self):
        history_all = self.get_all_run_history()
        total = len(history_all)
        success = len([history for history in history_all if history.is_success])
        failed = len([history for history in history_all if not history.is_success])
        return {'total': total, 'success': success, 'failed': failed}

    class Meta:
        db_table = 'ops_task'


class AdHoc(models.Model):
    """
    task: A task reference
    _tasks: [{'name': 'task_name', 'action': {'module': '', 'args': ''}, 'other..': ''}, ]
    _options: ansible options, more see ops.ansible.runner.Options
    _hosts: ["hostname1", "hostname2"], hostname must be unique key of cmdb
    run_as_admin: if true, then need get every host admin user run it, because every host may be have different admin user, so we choise host level
    run_as: if not run as admin, it run it as a system/common user from cmdb
    _become: May be using become [sudo, su] options. {method: "sudo", user: "user", pass: "pass"]
    pattern: Even if we set _hosts, We only use that to make inventory, We also can set `patter` to run task on match hosts
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(Task, related_name='adhoc', on_delete=models.CASCADE)
    _tasks = models.TextField(verbose_name=_('Tasks'))
    pattern = models.CharField(max_length=64, default='', verbose_name=_('Pattern'))
    _options = models.CharField(max_length=1024, default='', verbose_name=_('Options'))
    _hosts = models.TextField(blank=True, verbose_name=_('Hosts'))  # ['hostname1', 'hostname2']
    run_as_admin = models.BooleanField(default=False, verbose_name=_('Run as admin'))
    run_as = models.CharField(max_length=128, default='', verbose_name=_("Run as"))
    _become = models.CharField(max_length=1024, default='', verbose_name=_("Become"))
    created_by = models.CharField(max_length=64, default='', verbose_name=_('Create by'))
    date_created = models.DateTimeField(auto_now_add=True)

    @property
    def tasks(self):
        return json.loads(self._tasks)

    @tasks.setter
    def tasks(self, item):
        if item and isinstance(item, list):
            self._tasks = json.dumps(item)
        else:
            raise SyntaxError('Tasks should be a list')

    @property
    def hosts(self):
        return json.loads(self._hosts)

    @hosts.setter
    def hosts(self, item):
        self._hosts = json.dumps(item)

    @property
    def become(self):
        if self._become:
            return json.loads(signer.unsign(self._become))
        else:
            return {}

    @become.setter
    def become(self, item):
        """
        :param item:  {
            method: "sudo",
            user: "user",
            pass: "pass",
        }
        :return:
        """
        self._become = signer.sign(json.dumps(item))

    @property
    def options(self):
        if self._options:
            return json.loads(self._options)
        else:
            return {}

    @options.setter
    def options(self, item):
        self._options = json.dumps(item)

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    def get_latest_history(self):
        return self.history.all().order_by('date_start').last()

    def __str__(self):
        return "{} of {}".format(self.task.name, self.short_id)

    class Meta:
        db_table = "ops_adhoc"


class AdHocRunHistory(models.Model):
    """
    AdHoc running history.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    adhoc = models.ForeignKey(AdHoc, related_name='history', on_delete=models.CASCADE)
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    _result = models.TextField(blank=True, null=True, verbose_name=_('Adhoc raw result'))
    _summary = models.TextField(blank=True, null=True, verbose_name=_('Adhoc result summary'))

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def result(self):
        return json.loads(self._result)

    @result.setter
    def result(self, item):
        self._result = json.dumps(item)

    @property
    def summary(self):
        return json.loads(self._summary)

    @summary.setter
    def summary(self, item):
        self._summary = json.dumps(item)

    def __str__(self):
        return self.short_id

    class Meta:
        db_table = "ops_adhoc_history"
