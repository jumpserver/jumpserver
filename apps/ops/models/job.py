import json
import os
import uuid
import logging

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from celery import current_task

__all__ = ["Job", "JobExecution"]

from common.db.models import JMSBaseModel
from ops.ansible import JMSInventory, AdHocRunner, PlaybookRunner
from ops.mixin import PeriodTaskModelMixin


class Job(JMSBaseModel, PeriodTaskModelMixin):
    class Types(models.TextChoices):
        adhoc = 'adhoc', _('Adhoc')
        playbook = 'playbook', _('Playbook')

    class RunasPolicies(models.TextChoices):
        privileged_only = 'privileged_only', _('Privileged Only')
        privileged_first = 'privileged_first', _('Privileged First')
        skip = 'skip', _('Skip')

    class Modules(models.TextChoices):
        shell = 'shell', _('Shell')
        winshell = 'win_shell', _('Powershell')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, null=True, verbose_name=_('Name'))
    instant = models.BooleanField(default=False)
    args = models.CharField(max_length=1024, default='', verbose_name=_('Args'), null=True, blank=True)
    module = models.CharField(max_length=128, choices=Modules.choices, default=Modules.shell,
                              verbose_name=_('Module'), null=True)
    chdir = models.CharField(default="", max_length=1024, verbose_name=_('Chdir'), null=True, blank=True)
    timeout = models.IntegerField(default=60, verbose_name=_('Timeout (Seconds)'))
    playbook = models.ForeignKey('ops.Playbook', verbose_name=_("Playbook"), null=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=128, choices=Types.choices, default=Types.adhoc, verbose_name=_("Type"))
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Assets"))
    runas = models.CharField(max_length=128, default='root', verbose_name=_('Runas'))
    runas_policy = models.CharField(max_length=128, choices=RunasPolicies.choices, default=RunasPolicies.skip,
                                    verbose_name=_('Runas policy'))
    use_parameter_define = models.BooleanField(default=False, verbose_name=(_('Use Parameter Define')))
    parameters_define = models.JSONField(default=dict, verbose_name=_('Parameters define'))
    comment = models.CharField(max_length=1024, default='', verbose_name=_('Comment'), null=True, blank=True)

    @property
    def last_execution(self):
        return self.executions.last()

    @property
    def date_last_run(self):
        return self.last_execution.date_created if self.last_execution else None

    @property
    def summary(self):
        summary = {
            "total": 0,
            "success": 0,
        }
        for execution in self.executions.all():
            summary["total"] += 1
            if execution.is_success:
                summary["success"] += 1
        return summary

    @property
    def average_time_cost(self):
        total_cost = 0
        finished_count = self.executions.filter(status__in=['success', 'failed']).count()
        for execution in self.executions.filter(status__in=['success', 'failed']).all():
            total_cost += execution.time_cost
        return total_cost / finished_count if finished_count else 0

    def get_register_task(self):
        from ..tasks import run_ops_job_execution
        name = "run_ops_job_period_{}".format(str(self.id)[:8])
        task = run_ops_job_execution.name
        args = (str(self.id),)
        kwargs = {}
        return name, task, args, kwargs

    @property
    def inventory(self):
        return JMSInventory(self.assets.all(), self.runas_policy, self.runas)

    def create_execution(self):
        return self.executions.create()

    class Meta:
        ordering = ['date_created']


class JobExecution(JMSBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task_id = models.UUIDField(null=True)
    status = models.CharField(max_length=16, verbose_name=_('Status'), default='running')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='executions', null=True)
    parameters = models.JSONField(default=dict, verbose_name=_('Parameters'))
    result = models.JSONField(blank=True, null=True, verbose_name=_('Result'))
    summary = models.JSONField(default=dict, verbose_name=_('Summary'))
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'), db_index=True)
    date_finished = models.DateTimeField(null=True, verbose_name=_("Date finished"))

    @property
    def job_type(self):
        return self.job.type

    def compile_shell(self):
        if self.job.type != 'adhoc':
            return
        result = "{}{}{} ".format('\'', self.job.args, '\'')
        result += "chdir={}".format(self.job.chdir)
        return result

    def get_runner(self):
        inv = self.job.inventory
        inv.write_to_file(self.inventory_path)
        if isinstance(self.parameters, str):
            extra_vars = json.loads(self.parameters)
        else:
            extra_vars = {}

        if self.job.type == 'adhoc':
            args = self.compile_shell()
            runner = AdHocRunner(
                self.inventory_path, self.job.module, module_args=args,
                pattern="all", project_dir=self.private_dir, extra_vars=extra_vars,
            )
        elif self.job.type == 'playbook':
            runner = PlaybookRunner(
                self.inventory_path, self.job.playbook.entry
            )
        else:
            raise Exception("unsupported job type")
        return runner

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def time_cost(self):
        if self.date_finished and self.date_start:
            return (self.date_finished - self.date_start).total_seconds()
        return None

    @property
    def timedelta(self):
        if self.date_start and self.date_finished:
            return self.date_finished - self.date_start
        return None

    @property
    def is_finished(self):
        return self.status in ['success', 'failed']

    @property
    def is_success(self):
        return self.status == 'success'

    @property
    def inventory_path(self):
        return os.path.join(self.private_dir, 'inventory', 'hosts')

    @property
    def private_dir(self):
        uniq = self.date_created.strftime('%Y%m%d_%H%M%S') + '_' + self.short_id
        job_name = self.job.name if self.job.name else 'instant'
        return os.path.join(settings.ANSIBLE_DIR, job_name, uniq)

    def set_error(self, error):
        this = self.__class__.objects.get(id=self.id)  # 重新获取一次，避免数据库超时连接超时
        this.status = 'failed'
        this.summary['error'] = str(error)
        this.finish_task()

    def set_result(self, cb):
        status_mapper = {
            'successful': 'success',
        }
        this = self.__class__.objects.get(id=self.id)
        this.status = status_mapper.get(cb.status, cb.status)
        this.summary = cb.summary
        this.result = cb.result
        this.finish_task()

    def finish_task(self):
        self.date_finished = timezone.now()
        self.save(update_fields=['result', 'status', 'summary', 'date_finished'])

    def set_celery_id(self):
        if not current_task:
            return
        task_id = current_task.request.root_id
        self.task_id = task_id

    def start(self, **kwargs):
        self.date_start = timezone.now()
        self.set_celery_id()
        self.save()
        runner = self.get_runner()
        try:
            cb = runner.run(**kwargs)
            self.set_result(cb)
            return cb
        except Exception as e:
            logging.error(e, exc_info=True)
            self.set_error(e)

    class Meta:
        ordering = ['-date_created']
