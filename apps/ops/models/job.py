import json
import logging
import os
import uuid

from celery import current_task
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

__all__ = ["Job", "JobExecution", "JobAuditLog"]

from simple_history.models import HistoricalRecords

from ops.ansible import JMSInventory, AdHocRunner, PlaybookRunner
from ops.mixin import PeriodTaskModelMixin
from ops.variables import *
from ops.const import Types, Modules, RunasPolicies, JobStatus
from orgs.mixins.models import JMSOrgBaseModel


class Job(JMSOrgBaseModel, PeriodTaskModelMixin):
    name = models.CharField(max_length=128, null=True, verbose_name=_('Name'))
    instant = models.BooleanField(default=False)
    args = models.CharField(max_length=1024, default='', verbose_name=_('Args'), null=True, blank=True)
    module = models.CharField(max_length=128, choices=Modules.choices, default=Modules.shell,
                              verbose_name=_('Module'), null=True)
    chdir = models.CharField(default="", max_length=1024, verbose_name=_('Chdir'), null=True, blank=True)
    timeout = models.IntegerField(default=-1, verbose_name=_('Timeout (Seconds)'))
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
    version = models.IntegerField(default=0)
    history = HistoricalRecords()

    def get_history(self, version):
        return self.history.filter(version=version).first()

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
        return self.executions.create(job_version=self.version)

    class Meta:
        verbose_name = _("Job")
        ordering = ['date_created']


class JobExecution(JMSOrgBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task_id = models.UUIDField(null=True)
    status = models.CharField(max_length=16, verbose_name=_('Status'), default=JobStatus.running)
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, related_name='executions', null=True)
    job_version = models.IntegerField(default=0)
    parameters = models.JSONField(default=dict, verbose_name=_('Parameters'))
    result = models.JSONField(blank=True, null=True, verbose_name=_('Result'))
    summary = models.JSONField(default=dict, verbose_name=_('Summary'))
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'), db_index=True)
    date_finished = models.DateTimeField(null=True, verbose_name=_("Date finished"))

    @property
    def current_job(self):
        if self.job.version != self.job_version:
            return self.job.get_history(self.job_version)
        return self.job

    @property
    def material(self):
        if self.current_job.type == 'adhoc':
            return "{}:{}".format(self.current_job.module, self.current_job.args)
        if self.current_job.type == 'playbook':
            return "{}:{}:{}".format(self.org.name, self.current_job.creator.name, self.current_job.playbook.name)

    @property
    def assent_result_detail(self):
        if not self.is_finished or self.summary.get('error'):
            return None
        result = {
            "summary": self.summary,
            "detail": [],
        }
        for asset in self.current_job.assets.all():
            asset_detail = {
                "name": asset.name,
                "status": "ok",
                "tasks": [],
            }
            if self.summary.get("excludes", None) and self.summary["excludes"].get(asset.name, None):
                asset_detail.update({"status": "excludes"})
                result["detail"].append(asset_detail)
                break
            if self.result["dark"].get(asset.name, None):
                asset_detail.update({"status": "failed"})
                for key, task in self.result["dark"][asset.name].items():
                    task_detail = {"name": key,
                                   "output": "{}{}".format(task.get("stdout", ""), task.get("stderr", ""))}
                    asset_detail["tasks"].append(task_detail)
            if self.result["failures"].get(asset.name, None):
                asset_detail.update({"status": "failed"})
                for key, task in self.result["failures"][asset.name].items():
                    task_detail = {"name": key,
                                   "output": "{}{}".format(task.get("stdout", ""), task.get("stderr", ""))}
                    asset_detail["tasks"].append(task_detail)

            if self.result["ok"].get(asset.name, None):
                for key, task in self.result["ok"][asset.name].items():
                    task_detail = {"name": key,
                                   "output": "{}{}".format(task.get("stdout", ""), task.get("stderr", ""))}
                    asset_detail["tasks"].append(task_detail)
            result["detail"].append(asset_detail)
        return result

    @property
    def job_type(self):
        return Types[self.job.type].label

    def compile_shell(self):
        if self.current_job.type != 'adhoc':
            return

        module = self.current_job.module
        # replace win_shell
        if module == 'win_shell':
            module = 'ansible.windows.win_shell'

        if self.current_job.module in ['python']:
            module = "shell"

        shell = self.current_job.args
        if self.current_job.chdir:
            if module == self.current_job.module:
                shell += " path={}".format(self.current_job.chdir)
            else:
                shell += " chdir={}".format(self.current_job.chdir)
        if self.current_job.module in ['python']:
            shell += " executable={}".format(self.current_job.module)
        return module, shell

    def get_runner(self):
        inv = self.current_job.inventory
        inv.write_to_file(self.inventory_path)
        self.summary = self.result = {"excludes": {}}
        if len(inv.exclude_hosts) > 0:
            self.summary.update({"excludes": inv.exclude_hosts})
            self.result.update({"excludes": inv.exclude_hosts})
            self.save()

        if isinstance(self.parameters, str):
            extra_vars = json.loads(self.parameters)
        else:
            extra_vars = {}

        static_variables = self.gather_static_variables()
        extra_vars.update(static_variables)

        if self.current_job.type == 'adhoc':

            module, args = self.compile_shell()

            runner = AdHocRunner(
                self.inventory_path,
                module,
                timeout=self.current_job.timeout,
                module_args=args,
                pattern="all",
                project_dir=self.private_dir,
                extra_vars=extra_vars,
            )
        elif self.current_job.type == 'playbook':
            runner = PlaybookRunner(
                self.inventory_path, self.current_job.playbook.entry
            )
        else:
            raise Exception("unsupported job type")
        return runner

    def gather_static_variables(self):
        default = {
            JMS_JOB_ID: str(self.current_job.id),
            JMS_JOB_NAME: self.current_job.name,
        }
        if self.creator:
            default.update({JMS_USERNAME: self.creator.username})
        return default

    @property
    def short_id(self):
        return str(self.id).split('-')[-1]

    @property
    def time_cost(self):
        if self.is_finished:
            return (self.date_finished - self.date_start).total_seconds()
        return (timezone.now() - self.date_start).total_seconds()

    @property
    def timedelta(self):
        if self.date_start and self.date_finished:
            return self.date_finished - self.date_start
        return None

    @property
    def is_finished(self):
        return self.status in [JobStatus.success, JobStatus.failed, JobStatus.timeout]

    @property
    def is_success(self):
        return self.status == JobStatus.success

    @property
    def inventory_path(self):
        return os.path.join(self.private_dir, 'inventory', 'hosts')

    @property
    def private_dir(self):
        uniq = self.date_created.strftime('%Y%m%d_%H%M%S') + '_' + self.short_id
        job_name = self.current_job.name if self.current_job.name else 'instant'
        return os.path.join(settings.ANSIBLE_DIR, job_name, uniq)

    def set_error(self, error):
        this = self.__class__.objects.get(id=self.id)  # 重新获取一次，避免数据库超时连接超时
        this.status = JobStatus.failed
        this.summary.update({'error': str(error)})
        this.finish_task()

    def set_result(self, cb):
        status_mapper = {
            'successful': JobStatus.success,
        }
        this = self.__class__.objects.get(id=self.id)
        this.status = status_mapper.get(cb.status, cb.status)
        this.summary.update(cb.summary)
        if this.result:
            this.result.update(cb.result)
        else:
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
        verbose_name = _("Job Execution")
        ordering = ['-date_created']


class JobAuditLog(JobExecution):
    @property
    def creator_name(self):
        return self.creator.name

    class Meta:
        proxy = True
        verbose_name = _("Job audit log")
