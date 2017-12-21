# ~*~ coding: utf-8 ~*~

import logging
import json
import uuid

import time
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core import serializers
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from common.utils import signer
from .ansible import AdHocRunner, AnsibleError

__all__ = ["Task", "AdHoc", "AdHocRunHistory"]


logger = logging.getLogger(__name__)


class Task(models.Model):
    """
    This task is different ansible task, Task like 'push system user', 'get asset info' ..
    One task can have some versions of adhoc, run a task only run the latest version adhoc
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    interval = models.ForeignKey(
        IntervalSchedule, on_delete=models.CASCADE,
        null=True, blank=True, verbose_name=_('Interval'),
    )
    crontab = models.ForeignKey(
        CrontabSchedule, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name=_('Crontab'), help_text=_('Use one of Interval/Crontab'),
    )
    is_periodic = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_by = models.CharField(max_length=128, blank=True, null=True, default='')
    date_created = models.DateTimeField(auto_now_add=True)
    __latest_adhoc = None

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def latest_adhoc(self):
        if not self.__latest_adhoc:
            self.__latest_adhoc = self.get_latest_adhoc()
        return self.__latest_adhoc

    @latest_adhoc.setter
    def latest_adhoc(self, item):
        self.__latest_adhoc = item

    @property
    def latest_history(self):
        try:
            return self.history.all().latest()
        except AdHocRunHistory.DoesNotExist:
            return None

    def get_latest_adhoc(self):
        try:
            return self.adhoc.all().latest()
        except AdHoc.DoesNotExist:
            return None

    @property
    def history_summary(self):
        history = self.get_run_history()
        total = len(history)
        success = len([history for history in history if history.is_success])
        failed = len([history for history in history if not history.is_success])
        return {'total': total, 'success': success, 'failed': failed}

    def get_run_history(self):
        return self.history.all()

    def run(self, record=True):
        if self.latest_adhoc:
            return self.latest_adhoc.run(record=record)
        else:
            return {'error': 'No adhoc'}

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        instance = super().save(
            force_insert=force_insert,  force_update=force_update,
            using=using, update_fields=update_fields,
        )

        if instance.is_periodic:
            PeriodicTask.objects.update_or_create(
                interval=instance.interval,
                crontab=instance.crontab,
                name=self.name,
                task='ops.run_task',
                args=serializers.serialize('json', [instance]),
            )
        else:
            PeriodicTask.objects.filter(name=self.name).delete()

        return instance

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ops_task'
        get_latest_by = 'date_created'


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
    pattern = models.CharField(max_length=64, default='{}', verbose_name=_('Pattern'))
    _options = models.CharField(max_length=1024, default='', verbose_name=_('Options'))
    _hosts = models.TextField(blank=True, verbose_name=_('Hosts'))  # ['hostname1', 'hostname2']
    run_as_admin = models.BooleanField(default=False, verbose_name=_('Run as admin'))
    run_as = models.CharField(max_length=128, default='', verbose_name=_("Run as"))
    _become = models.CharField(max_length=1024, default='', verbose_name=_("Become"))
    created_by = models.CharField(max_length=64, default='', null=True, verbose_name=_('Create by'))
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

    def run(self, record=True):
        if record:
            return self._run_and_record()
        else:
            return self._run_only()

    def _run_and_record(self):
        history = AdHocRunHistory(adhoc=self, task=self.task)
        time_start = time.time()
        try:
            result = self._run_only()
            history.is_finished = True
            if result.results_summary.get('dark'):
                history.is_success = False
            else:
                history.is_success = True
            history.result = result.results_raw
            history.summary = result.results_summary
            return result
        finally:
            history.date_finished = timezone.now()
            history.timedelta = time.time() - time_start
            history.save()

    def _run_only(self):
        from .utils import get_adhoc_inventory
        inventory = get_adhoc_inventory(self)
        runner = AdHocRunner(inventory)
        for k, v in self.options.items():
            runner.set_option(k, v)

        try:
            result = runner.run(self.tasks, self.pattern, self.task.name)
            return result
        except AnsibleError as e:
            logger.error("Failed run adhoc {}, {}".format(self.task.name, e))

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
            _options = json.loads(self._options)
            if isinstance(_options, dict):
                return _options
        return {}

    @options.setter
    def options(self, item):
        self._options = json.dumps(item)

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def latest_history(self):
        try:
            return self.history.all().latest()
        except AdHocRunHistory.DoesNotExist:
            return None

    def __str__(self):
        return "{} of {}".format(self.task.name, self.short_id)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        fields_check = []
        for field in self.__class__._meta.fields:
            if field.name not in ['id', 'date_created']:
                fields_check.append(field)
        for field in fields_check:
            if getattr(self, field.name) != getattr(other, field.name):
                return False
        return True

    class Meta:
        db_table = "ops_adhoc"
        get_latest_by = 'date_created'


class AdHocRunHistory(models.Model):
    """
    AdHoc running history.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(Task, related_name='history', on_delete=models.SET_NULL, null=True)
    adhoc = models.ForeignKey(AdHoc, related_name='history', on_delete=models.SET_NULL, null=True)
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

    @property
    def success_hosts(self):
        return self.summary.get('contacted', [])

    @property
    def failed_hosts(self):
        return self.summary.get('dark', {})

    def __str__(self):
        return self.short_id

    class Meta:
        db_table = "ops_adhoc_history"
        get_latest_by = 'date_start'
