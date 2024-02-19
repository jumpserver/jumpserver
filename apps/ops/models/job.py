import json
import logging
import os
import sys
import uuid
from collections import defaultdict
from datetime import timedelta

from celery import current_task
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

__all__ = ["Job", "JobExecution", "JMSPermedInventory"]

from simple_history.models import HistoricalRecords

from accounts.models import Account
from acls.models import CommandFilterACL
from assets.models import Asset
from assets.automations.base.manager import SSHTunnelManager
from common.db.encoder import ModelJSONFieldEncoder
from ops.ansible import JMSInventory, AdHocRunner, PlaybookRunner, CommandInBlackListException, UploadFileRunner
from ops.mixin import PeriodTaskModelMixin
from ops.variables import *
from ops.const import Types, RunasPolicies, JobStatus, JobModules
from orgs.mixins.models import JMSOrgBaseModel
from perms.models import AssetPermission
from perms.utils import UserPermAssetUtil
from terminal.notifications import CommandExecutionAlert
from terminal.notifications import CommandWarningMessage
from terminal.const import RiskLevelChoices


def get_parent_keys(key, include_self=True):
    keys = []
    split_keys = key.split(':')
    for i in range(len(split_keys)):
        keys.append(':'.join(split_keys[:i + 1]))
    if not include_self:
        keys.pop()
    return keys


class JMSPermedInventory(JMSInventory):
    def __init__(self,
                 assets,
                 account_policy='privileged_first',
                 account_prefer='root,Administrator',
                 module=None,
                 host_callback=None,
                 user=None):
        super().__init__(assets, account_policy, account_prefer, host_callback, exclude_localhost=True)
        self.user = user
        self.module = module
        self.assets_accounts_mapper = self.get_assets_accounts_mapper()

    def make_account_vars(self, host, asset, account, automation, protocol, platform, gateway):
        if not account:
            host['error'] = _("No account available")
            return host

        protocol_supported_modules_mapping = {
            'mysql': ['mysql'],
            'postgresql': ['postgresql'],
            'sqlserver': ['sqlserver'],
            'ssh': ['shell', 'python', 'win_shell', 'raw'],
            'winrm': ['win_shell', 'shell'],
        }

        if self.module not in protocol_supported_modules_mapping.get(protocol.name, []):
            host['error'] = "Module {} is not suitable for this asset".format(self.module)
            return host

        if protocol.name in ('mysql', 'postgresql', 'sqlserver'):
            host['login_host'] = asset.address
            host['login_port'] = protocol.port
            host['login_user'] = account.username
            host['login_password'] = account.secret
            host['login_db'] = asset.spec_info.get('db_name', '')
            host['ansible_python_interpreter'] = sys.executable
            if gateway:
                host['gateway'] = {
                    'address': gateway.address, 'port': gateway.port,
                    'username': gateway.username, 'secret': gateway.password,
                    'private_key_path': gateway.private_key_path
                }
                host['jms_asset']['port'] = protocol.port
            return host
        return super().make_account_vars(host, asset, account, automation, protocol, platform, gateway)

    def get_asset_sorted_accounts(self, asset):
        accounts = self.assets_accounts_mapper.get(asset.id, [])
        return list(accounts)

    def get_assets_accounts_mapper(self):
        mapper = defaultdict(set)
        asset_ids = self.assets.values_list('id', flat=True)
        asset_node_keys = Asset.nodes.through.objects \
            .filter(asset_id__in=asset_ids) \
            .values_list('asset_id', 'node__key')

        node_asset_map = defaultdict(set)
        for asset_id, node_key in asset_node_keys:
            all_keys = get_parent_keys(node_key)
            for key in all_keys:
                node_asset_map[key].add(asset_id)

        groups = self.user.groups.all()
        perms = AssetPermission.objects \
            .filter(date_expired__gte=timezone.now()) \
            .filter(is_active=True) \
            .filter(Q(users=self.user) | Q(user_groups__in=groups)) \
            .filter(Q(assets__in=asset_ids) | Q(nodes__key__in=node_asset_map.keys())) \
            .values_list('assets', 'nodes__key', 'accounts')

        asset_permed_accounts_mapper = defaultdict(set)
        for asset_id, node_key, accounts in perms:
            if asset_id in asset_ids:
                asset_permed_accounts_mapper[asset_id].update(accounts)
            for my_asset in node_asset_map[node_key]:
                asset_permed_accounts_mapper[my_asset].update(accounts)

        accounts = Account.objects.filter(asset__in=asset_ids)
        for account in accounts:
            if account.asset_id not in asset_permed_accounts_mapper:
                continue
            permed_usernames = asset_permed_accounts_mapper[account.asset_id]
            if "@ALL" in permed_usernames or account.username in permed_usernames:
                mapper[account.asset_id].add(account)
        return mapper


class Job(JMSOrgBaseModel, PeriodTaskModelMixin):
    name = models.CharField(max_length=128, null=True, verbose_name=_('Name'))
    instant = models.BooleanField(default=False)
    args = models.CharField(max_length=8192, default='', verbose_name=_('Args'), null=True, blank=True)
    module = models.CharField(max_length=128, choices=JobModules.choices, default=JobModules.shell,
                              verbose_name=_('Module'), null=True)
    chdir = models.CharField(default="", max_length=1024, verbose_name=_('Chdir'), null=True, blank=True)
    timeout = models.IntegerField(default=-1, verbose_name=_('Timeout (Seconds)'))
    playbook = models.ForeignKey('ops.Playbook', verbose_name=_("Playbook"), null=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=128, choices=Types.choices, default=Types.adhoc, verbose_name=_("Type"))
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    assets = models.ManyToManyField('assets.Asset', verbose_name=_("Assets"))
    use_parameter_define = models.BooleanField(default=False, verbose_name=(_('Use Parameter Define')))
    parameters_define = models.JSONField(default=dict, verbose_name=_('Parameters define'))
    runas = models.CharField(max_length=128, default='root', verbose_name=_('Runas'))
    runas_policy = models.CharField(max_length=128, choices=RunasPolicies.choices, default=RunasPolicies.skip,
                                    verbose_name=_('Runas policy'))
    comment = models.CharField(max_length=1024, default='', verbose_name=_('Comment'), null=True, blank=True)
    version = models.IntegerField(default=0)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

    def get_history(self, version):
        return self.history.filter(version=version).first()

    @property
    def last_execution(self):
        return self.executions.first()

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
        from ..tasks import run_ops_job
        name = "run_ops_job_period_{}".format(str(self.id)[:8])
        task = run_ops_job.name
        args = (str(self.id),)
        kwargs = {}
        return name, task, args, kwargs

    @property
    def inventory(self):
        return JMSPermedInventory(self.assets.all(),
                                  self.runas_policy, self.runas,
                                  user=self.creator, module=self.module)

    @property
    def material(self):
        if self.type == 'adhoc':
            return "{}:{}".format(self.module, self.args)
        if self.type == 'playbook':
            return "{}:{}:{}".format(self.org.name, self.creator.name, self.playbook.name)

    def create_execution(self):
        return self.executions.create(job_version=self.version, material=self.material, job_type=Types[self.type].value)

    class Meta:
        verbose_name = _("Job")
        unique_together = [('name', 'org_id', 'creator')]
        ordering = ['date_created']


zombie_task_exception = Exception(
    'This task has been marked as a zombie task because it has not updated its status for too long')


class JobExecution(JMSOrgBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    task_id = models.UUIDField(null=True)
    status = models.CharField(max_length=16, verbose_name=_('Status'), default=JobStatus.running)
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, related_name='executions', null=True)
    job_version = models.IntegerField(default=0)
    parameters = models.JSONField(default=dict, verbose_name=_('Parameters'))
    result = models.JSONField(encoder=ModelJSONFieldEncoder, blank=True, null=True, verbose_name=_('Result'))
    summary = models.JSONField(encoder=ModelJSONFieldEncoder, default=dict, verbose_name=_('Summary'))
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'), db_index=True)
    date_finished = models.DateTimeField(null=True, verbose_name=_("Date finished"))

    material = models.CharField(max_length=8192, default='', verbose_name=_('Material'), null=True, blank=True)
    job_type = models.CharField(max_length=128, choices=Types.choices, default=Types.adhoc,
                                verbose_name=_("Material Type"))

    # clean up zombie execution

    @classmethod
    def clean_unexpected_execution(cls):
        for execution in cls.objects.filter(status__in=[JobStatus.running]).all():
            if execution.date_created < (timezone.now() - timedelta(hours=3)):
                execution.set_error(zombie_task_exception)

    @property
    def current_job(self):
        if self.job.version != self.job_version:
            return self.job.get_history(self.job_version)
        return self.job

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

    def compile_shell(self):
        if self.current_job.type != 'adhoc':
            return

        module = self.current_job.module

        db_modules = ('mysql', 'postgresql', 'sqlserver', 'oracle')
        db_module_name_map = {
            'mysql': 'community.mysql.mysql_query',
            'postgresql': 'community.postgresql.postgresql_query',
            'sqlserver': 'community.general.mssql_script',
        }
        extra_query_token_map = {
            'sqlserver': 'script'
        }
        extra_login_db_token_map = {
            'sqlserver': 'name'
        }

        if module in db_modules:
            login_db_token = extra_login_db_token_map.get(module, 'login_db')
            query_token = extra_query_token_map.get(module, 'query')
            module = db_module_name_map.get(module, None)
            if not module:
                print('not support db module: {}'.format(module))
                raise Exception('not support db module: {}'.format(module))

            login_args = "login_host={{login_host}} " \
                         "login_user={{login_user}} " \
                         "login_password={{login_password}} " \
                         "login_port={{login_port}} " \
                         "%s={{login_db}}" % login_db_token
            shell = "{} {}=\"{}\" ".format(login_args, query_token, self.current_job.args)
            return module, shell

        if module == 'win_shell':
            module = 'ansible.windows.win_shell'

        if self.current_job.module in ['python']:
            module = "shell"

        shell = self.current_job.args
        if self.current_job.chdir:
            if module == "shell":
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

        if self.current_job.type == Types.adhoc:
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
        elif self.current_job.type == Types.playbook:
            runner = PlaybookRunner(
                self.inventory_path, self.current_job.playbook.entry
            )
        elif self.current_job.type == Types.upload_file:
            job_id = self.current_job.id
            args = json.loads(self.current_job.args)
            dst_path = args.get('dst_path', '/')
            runner = UploadFileRunner(self.inventory_path, job_id, dst_path)
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
        if not self.date_start:
            return 0
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

    def match_command_group(self, acl, asset):
        for cg in acl.command_groups.all():
            matched, __ = cg.match(self.current_job.args)
            if matched:
                if acl.is_action(CommandFilterACL.ActionChoices.accept):
                    return True
                elif acl.is_action(CommandFilterACL.ActionChoices.reject) or acl.is_action(
                        CommandFilterACL.ActionChoices.review):
                    print("\033[31mcommand \'{}\' on asset {}({}) is rejected by acl {}\033[0m"
                          .format(self.current_job.args, asset.name, asset.address, acl))
                    CommandExecutionAlert({
                        "assets": self.current_job.assets.all(),
                        "input": self.material,
                        "risk_level": RiskLevelChoices.reject,
                        "user": self.creator,
                    }).publish_async()
                    raise Exception("command is rejected by ACL")
                elif acl.is_action(CommandFilterACL.ActionChoices.warning):
                    command = {
                        'input': self.material,
                        'user': self.creator.name,
                        'asset': asset.name,
                        'cmd_filter_acl': str(acl.id),
                        'cmd_group': str(cg.id),
                        'risk_level': RiskLevelChoices.warning,
                        'org_id': self.org_id,
                        '_account': self.current_job.runas,
                        '_cmd_filter_acl': acl,
                        '_cmd_group': cg,
                        '_org_name': self.org_name,
                    }
                    for reviewer in acl.reviewers.all():
                        CommandWarningMessage(reviewer, command).publish_async()
                    return True
        return False

    def check_command_acl(self):
        for asset in self.current_job.assets.all():
            acls = CommandFilterACL.filter_queryset(
                user=self.creator,
                asset=asset,
                is_active=True,
                account_username=self.current_job.runas)
            for acl in acls:
                if self.match_command_group(acl, asset):
                    break

    def check_danger_keywords(self):
        lines = self.job.playbook.check_dangerous_keywords()
        if len(lines) > 0:
            for line in lines:
                print('\033[31mThe {} line of the file \'{}\' contains the '
                      'dangerous keyword \'{}\'\033[0m'.format(line['line'], line['file'], line['keyword']))
            raise Exception("Playbook contains dangerous keywords")

    def check_assets_perms(self):
        all_permed_assets = UserPermAssetUtil(self.creator).get_all_assets()
        has_permed_assets = set(self.current_job.assets.all()) & set(all_permed_assets)

        error_assets_count = 0
        for asset in self.current_job.assets.all():
            if asset not in has_permed_assets:
                print("\033[31mAsset {}({}) has no access permission\033[0m".format(asset.name, asset.address))
                error_assets_count += 1

        if error_assets_count > 0:
            raise Exception("You do not have access rights to {} assets".format(error_assets_count))

    def before_start(self):
        self.check_assets_perms()
        if self.current_job.type == 'playbook':
            self.check_danger_keywords()
        if self.current_job.type == 'adhoc':
            self.check_command_acl()

    def start(self, **kwargs):
        self.date_start = timezone.now()
        self.set_celery_id()
        self.save()
        self.before_start()

        runner = self.get_runner()
        ssh_tunnel = SSHTunnelManager()
        ssh_tunnel.local_gateway_prepare(runner)
        try:
            cb = runner.run(**kwargs)
            self.set_result(cb)
            return cb
        except CommandInBlackListException as e:
            print(e)
            self.set_error(e)
        except Exception as e:
            logging.error(e, exc_info=True)
            self.set_error(e)
        finally:
            ssh_tunnel.local_gateway_clean(runner)

    def stop(self):
        with open(os.path.join(self.private_dir, 'local.pid')) as f:
            try:
                pid = f.read()
                os.kill(int(pid), 9)
            except Exception as e:
                print(e)
        self.set_error('Job stop by "kill -9 {}"'.format(pid))

    class Meta:
        verbose_name = _("Job Execution")
        ordering = ['-date_created']
