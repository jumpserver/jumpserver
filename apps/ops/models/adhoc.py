# ~*~ coding: utf-8 ~*~

import uuid
import os
import time
import datetime

from celery import current_task
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, lazyproperty
from common.fields.model import (
    JsonListTextField, JsonDictCharField, EncryptJsonDictCharField,
    JsonDictTextField,
)
from orgs.mixins.models import OrgModelMixin
from ..ansible import AdHocRunner, AnsibleError
from ..inventory import JMSInventory
from ..mixin import PeriodTaskModelMixin

__all__ = ["Task", "AdHoc", "AdHocExecution"]


logger = get_logger(__file__)


class Task(PeriodTaskModelMixin, OrgModelMixin):
    """
    This task is different ansible task, Task like 'push system user', 'get asset info' ..
    One task can have some versions of adhoc, run a task only run the latest version adhoc
    """
    callback = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Callback"))  # Callback must be a registered celery task
    is_deleted = models.BooleanField(default=False)
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    date_created = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_("Date created"))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))
    latest_adhoc = models.ForeignKey('ops.AdHoc', on_delete=models.SET_NULL, null=True, related_name='task_latest')
    latest_execution = models.ForeignKey('ops.AdHocExecution', on_delete=models.SET_NULL, null=True, related_name='task_latest')
    total_run_amount = models.IntegerField(default=0)
    success_run_amount = models.IntegerField(default=0)
    _ignore_auto_created_by = True

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @lazyproperty
    def versions(self):
        return self.adhoc.all().count()

    @property
    def is_success(self):
        if self.latest_execution:
            return self.latest_execution.is_success
        else:
            return False

    @property
    def timedelta(self):
        if self.latest_execution:
            return self.latest_execution.timedelta
        else:
            return 0

    @property
    def date_start(self):
        if self.latest_execution:
            return self.latest_execution.date_start
        else:
            return None

    @property
    def assets_amount(self):
        if self.latest_execution:
            return self.latest_execution.hosts_amount
        return 0

    def get_latest_adhoc(self):
        if self.latest_adhoc:
            return self.latest_adhoc
        try:
            adhoc = self.adhoc.all().latest()
            self.latest_adhoc = adhoc
            self.save()
            return adhoc
        except AdHoc.DoesNotExist:
            return None

    @property
    def history_summary(self):
        total = self.total_run_amount
        success = self.success_run_amount
        failed = total - success
        return {'total': total, 'success': success, 'failed': failed}

    def get_run_execution(self):
        return self.execution.all()

    def run(self):
        latest_adhoc = self.get_latest_adhoc()
        if latest_adhoc:
            return latest_adhoc.run()
        else:
            return {'error': 'No adhoc'}

    @property
    def period_key(self):
        return self.__str__()

    def get_register_task(self):
        from ..tasks import run_ansible_task
        name = self.__str__()
        task = run_ansible_task.name
        args = (str(self.id),)
        kwargs = {"callback": self.callback}
        return name, task, args, kwargs

    def __str__(self):
        return self.name + '@' + str(self.org_id)

    class Meta:
        db_table = 'ops_task'
        unique_together = ('name', 'org_id')
        ordering = ('-date_updated',)
        get_latest_by = 'date_created'


class AdHoc(OrgModelMixin):
    """
    task: A task reference
    _tasks: [{'name': 'task_name', 'action': {'module': '', 'args': ''}, 'other..': ''}, ]
    _options: ansible options, more see ops.ansible.runner.Options
    run_as_admin: if true, then need get every host admin user run it, because every host may be have different admin user, so we choise host level
    run_as: username(Add the uniform AssetUserManager <AssetUserManager> and change it to username)
    _become: May be using become [sudo, su] options. {method: "sudo", user: "user", pass: "pass"]
    pattern: Even if we set _hosts, We only use that to make inventory, We also can set `patter` to run task on match hosts
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(Task, related_name='adhoc', on_delete=models.CASCADE)
    tasks = JsonListTextField(verbose_name=_('Tasks'))
    pattern = models.CharField(max_length=64, default='{}', verbose_name=_('Pattern'))
    options = JsonDictCharField(max_length=1024, default='', verbose_name=_('Options'))
    hosts = models.ManyToManyField('assets.Asset', verbose_name=_("Host"))
    run_as_admin = models.BooleanField(default=False, verbose_name=_('Run as admin'))
    run_as = models.CharField(max_length=64, default='', blank=True, null=True, verbose_name=_('Username'))
    become = EncryptJsonDictCharField(max_length=1024, default='', blank=True, null=True, verbose_name=_("Become"))
    created_by = models.CharField(max_length=64, default='', blank=True, null=True, verbose_name=_('Create by'))
    date_created = models.DateTimeField(auto_now_add=True, db_index=True)

    @lazyproperty
    def run_times(self):
        return self.execution.count()

    @property
    def inventory(self):
        if self.become:
            become_info = {
                'become': {
                    self.become
                }
            }
        else:
            become_info = None

        inventory = JMSInventory(
            self.hosts.all(), run_as_admin=self.run_as_admin,
            run_as=self.run_as, become_info=become_info
        )
        return inventory

    @property
    def become_display(self):
        if self.become:
            return self.become.get("user", "")
        return ""

    def run(self):
        try:
            celery_task_id = current_task.request.id
        except AttributeError:
            celery_task_id = None

        execution = AdHocExecution(
            celery_task_id=celery_task_id,
            adhoc=self, task=self.task,
            task_display=str(self.task)[:128],
            date_start=timezone.now(),
            hosts_amount=self.hosts.count(),
        )
        execution.save()
        return execution.start()

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def latest_execution(self):
        try:
            return self.execution.all().latest()
        except AdHocExecution.DoesNotExist:
            return None

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        self.task.latest_adhoc = instance
        self.task.save()
        return instance

    def __str__(self):
        return "{} of {}".format(self.task.name, self.short_id)

    def same_with(self, other):
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


class AdHocExecution(OrgModelMixin):
    """
    AdHoc running history.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task = models.ForeignKey(Task, related_name='execution', on_delete=models.SET_NULL, null=True)
    task_display = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Task display"))
    celery_task_id = models.UUIDField(default=None, null=True)
    hosts_amount = models.IntegerField(default=0, verbose_name=_("Host amount"))
    adhoc = models.ForeignKey(AdHoc, related_name='execution', on_delete=models.SET_NULL, null=True)
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Start time'))
    date_finished = models.DateTimeField(blank=True, null=True, verbose_name=_('End time'))
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    result = JsonDictTextField(blank=True, null=True, verbose_name=_('Adhoc raw result'))
    summary = JsonDictTextField(blank=True, null=True, verbose_name=_('Adhoc result summary'))

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def adhoc_short_id(self):
        return str(self.adhoc_id).split('-')[-1]

    @property
    def log_path(self):
        dt = datetime.datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(settings.PROJECT_DIR, 'data', 'ansible', dt)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return os.path.join(log_dir, str(self.id) + '.log')

    def start_runner(self):
        runner = AdHocRunner(self.adhoc.inventory, options=self.adhoc.options)
        try:
            result = runner.run(
                self.adhoc.tasks,
                self.adhoc.pattern,
                self.task.name,
                execution_id=self.id
            )
            return result.results_raw, result.results_summary
        except AnsibleError as e:
            logger.warn("Failed run adhoc {}, {}".format(self.task.name, e))
            return {}, {}

    def start(self):
        self.task.latest_execution = self
        self.task.save()
        time_start = time.time()
        summary = {}
        raw = ''

        try:
            date_start_s = timezone.now().now().strftime('%Y-%m-%d %H:%M:%S')
            print(_("{} Start task: {}").format(date_start_s, self.task.name))
            raw, summary = self.start_runner()
        except Exception as e:
            logger.error(e, exc_info=True)
            raw = {"dark": {"all": str(e)}, "contacted": []}
        finally:
            self.clean_up(summary, time_start)
            date_end = timezone.now().now()
            date_end_s = date_end.strftime('%Y-%m-%d %H:%M:%S')
            print(_("{} Task finish").format(date_end_s))
            print('.\n\n.')
            return raw, summary

    def clean_up(self, summary, time_start):
        is_success = summary.get('success', False)
        task = Task.objects.get(id=self.task_id)
        task.total_run_amount = models.F('total_run_amount') + 1
        if is_success:
            task.success_run_amount = models.F('success_run_amount') + 1
        task.save()
        AdHocExecution.objects.filter(id=self.id).update(
            is_finished=True,
            is_success=is_success,
            date_finished=timezone.now(),
            timedelta=time.time() - time_start,
            summary=summary
        )

    @property
    def success_hosts(self):
        return self.summary.get('contacted', [])

    @property
    def failed_hosts(self):
        return self.summary.get('dark', {})

    def __str__(self):
        return self.short_id

    class Meta:
        db_table = "ops_adhoc_execution"
        get_latest_by = 'date_start'
