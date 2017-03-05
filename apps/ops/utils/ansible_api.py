# ~*~ coding: utf-8 ~*~
# from __future__ import unicode_literals, print_function

import os
import json
import logging
import traceback
import ansible.constants as default_config
from collections import namedtuple

from uuid import uuid4
from django.utils import timezone
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory, Host, Group
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor import playbook_executor
from ansible.utils.display import Display
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
import ansible.constants as C
from ansible.utils.vars import load_extra_vars
from ansible.utils.vars import load_options_vars

from ..models import TaskRecord, AnsiblePlay, AnsibleTask, AnsibleHostResult

__all__ = ["ADHocRunner", "Options"]

C.HOST_KEY_CHECKING = False

logger = logging.getLogger(__name__)


class AnsibleError(StandardError):
    pass


# class Options(object):
#     """Ansible运行时配置类, 用于初始化Ansible的一些默认配置.
#     """
#     def __init__(self, verbosity=None, inventory=None, listhosts=None, subset=None, module_paths=None, extra_vars=None,
#                  forks=10, ask_vault_pass=False, vault_password_files=None, new_vault_password_file=None,
#                  output_file=None, tags=None, skip_tags=None, one_line=None, tree=None, ask_sudo_pass=False, ask_su_pass=False,
#                  sudo=None, sudo_user=None, become=None, become_method=None, become_user=None, become_ask_pass=False,
#                  ask_pass=False, private_key_file=None, remote_user=None, connection="smart", timeout=10, ssh_common_args=None,
#                  sftp_extra_args=None, scp_extra_args=None, ssh_extra_args=None, poll_interval=None, seconds=None, check=False,
#                  syntax=None, diff=None, force_handlers=None, flush_cache=None, listtasks=None, listtags=None, module_path=None):
#         self.verbosity = verbosity
#         self.inventory = inventory
#         self.listhosts = listhosts
#         self.subset = subset
#         self.module_paths = module_paths
#         self.extra_vars = extra_vars
#         self.forks = forks
#         self.ask_vault_pass = ask_vault_pass
#         self.vault_password_files = vault_password_files
#         self.new_vault_password_file = new_vault_password_file
#         self.output_file = output_file
#         self.tags = tags
#         self.skip_tags = skip_tags
#         self.one_line = one_line
#         self.tree = tree
#         self.ask_sudo_pass = ask_sudo_pass
#         self.ask_su_pass = ask_su_pass
#         self.sudo = sudo
#         self.sudo_user = sudo_user
#         self.become = become
#         self.become_method = become_method
#         self.become_user = become_user
#         self.become_ask_pass = become_ask_pass
#         self.ask_pass = ask_pass
#         self.private_key_file = private_key_file
#         self.remote_user = remote_user
#         self.connection = connection
#         self.timeout = timeout
#         self.ssh_common_args = ssh_common_args
#         self.sftp_extra_args = sftp_extra_args
#         self.scp_extra_args = scp_extra_args
#         self.ssh_extra_args = ssh_extra_args
#         self.poll_interval = poll_interval
#         self.seconds = seconds
#         self.check = check
#         self.syntax = syntax
#         self.diff = diff
#         self.force_handlers = force_handlers
#         self.flush_cache = flush_cache
#         self.listtasks = listtasks
#         self.listtags = listtags
#         self.module_path = module_path
#         self.__overwrite_default()
#
#     def __overwrite_default(self):
#         """上面并不能包含Ansible所有的配置, 如果有其他的配置,
#         可以通过替换default_config模块里面的变量进行重载，　
#         比如 default_config.DEFAULT_ASK_PASS = False.
#         """
#         default_config.HOST_KEY_CHECKING = False
Options = namedtuple("Options", [
    'connection', 'module_path', 'private_key_file', "remote_user", "timeout",
    'forks', 'become', 'become_method', 'become_user', 'check', "extra_vars",
    ]
)


class JMSHost(Host):
    def __init__(self, asset):
        self.asset = asset
        self.name = name = asset.get('hostname') or asset.get('ip')
        self.port = port = asset.get('port') or 22
        super(JMSHost, self).__init__(name, port)
        self.set_all_variable()

    def set_all_variable(self):
        asset = self.asset
        self.set_variable('ansible_host', asset['ip'])
        self.set_variable('ansible_port', asset['port'])
        self.set_variable('ansible_user', asset['username'])

        # 添加密码和秘钥
        if asset.get('password'):
            self.set_variable('ansible_ssh_pass', asset['password'])
        if asset.get('key'):
            self.set_variable('ansible_ssh_private_key_file', asset['private_key'])

        # 添加become支持
        become = asset.get("become", None)
        if become is not None:
            self.set_variable("ansible_become", True)
            self.set_variable("ansible_become_method", become.get('method'))
            self.set_variable("ansible_become_user", become.get('user'))
            self.set_variable("ansible_become_pass", become.get('pass'))
        else:
            self.set_variable("ansible_become", False)


class JMSInventory(Inventory):
    """
    提供生成Ansible inventory对象的方法
    """

    def __init__(self, host_list=None):
        if host_list is None:
            host_list = []
        assert isinstance(host_list, list)
        self.host_list = host_list
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        super(JMSInventory, self).__init__(self.loader, self.variable_manager,
                                           host_list=host_list)

    def parse_inventory(self, host_list):
        """用于生成动态构建Ansible Inventory.
        self.host_list: [
            {"name": "asset_name",
             "ip": <ip>,
             "port": <port>,
             "user": <user>,
             "pass": <pass>,
             "key": <sshKey>,
             "groups": ['group1', 'group2'],
             "other_host_var": <other>},
             {...},
        ]

        :return: 返回一个Ansible的inventory对象
        """

        # TODO: 验证输入
        # 创建Ansible Group,如果没有则创建default组
        ungrouped = Group('ungrouped')
        all = Group('all')
        all.add_child_group(ungrouped)
        self.groups = dict(all=all, ungrouped=ungrouped)

        for asset in host_list:
            host = JMSHost(asset=asset)
            asset_groups = asset.get('groups')
            if asset_groups:
                for group_name in asset_groups:
                    if group_name not in self.groups:
                        group = Group(group_name)
                        self.groups[group_name] = group
                    else:
                        group = self.groups[group_name]
                    group.add_host(host)
            else:
                ungrouped.add_host(host)
            all.add_host(host)


class BasicResultCallback(CallbackBase):
    """
    Custom Callback
    """
    def __init__(self, display=None):
        self.result_q = dict(contacted={}, dark={})
        super(BasicResultCallback, self).__init__(display)

    def gather_result(self, n, res):
        self.result_q[n].update({res._host.name: res._result})

    def v2_runner_on_ok(self, result):
        self.gather_result("contacted", result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.gather_result("dark", result)

    def v2_runner_on_unreachable(self, result):
        self.gather_result("dark", result)

    def v2_runner_on_skipped(self, result):
        self.gather_result("dark", result)

    def v2_playbook_on_task_start(self, task, is_conditional):
        pass

    def v2_playbook_on_play_start(self, play):
        pass


class CallbackModule(CallbackBase):
    """处理和分析Ansible运行结果,并保存数据.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'json'

    def __init__(self, tasker_id, display=None):
        super(CallbackModule, self).__init__(display)
        self.results = []
        self.output = {}
        self.tasker_id = tasker_id

    def _new_play(self, play):
        """将Play保持到数据里面
        """
        ret = {
            'tasker': self.tasker_id,
            'name': play.name,
            'uuid': str(play._uuid),
            'tasks': []
        }

        try:
            tasker = TaskRecord.objects.get(uuid=self.tasker_id)
            play = AnsiblePlay(tasker, name=ret['name'], uuid=ret['uuid'])
            play.save()
        except Exception as e:
            traceback.print_exc()
            logger.error("Save ansible play uuid to database error!, %s" % e.message)

        return ret

    def _new_task(self, task):
        """将Task保持到数据库里,需要和Play进行关联
        """
        ret = {
            'name': task.name,
            'uuid': str(task._uuid),
            'failed': {},
            'unreachable': {},
            'skipped': {},
            'no_hosts': {},
            'success': {}
        }

        try:
            play = AnsiblePlay.objects.get(uuid=self.__play_uuid)
            task = AnsibleTask(play=play, uuid=ret['uuid'], name=ret['name'])
            task.save()
        except Exception as e:
            logger.error("Save ansible task uuid to database error!, %s" % e.message)

        return ret

    @property
    def __task_uuid(self):
        return self.results[-1]['tasks'][-1]['uuid']

    @property
    def __play_uuid(self):
        return self.results[-1]['uuid']

    def save_task_result(self, result, status):
        try:
            task = AnsibleTask.objects.get(uuid=self.__task_uuid)
            host_result = AnsibleHostResult(task=task, name=result._host)
            if status == "failed":
                host_result.failed = json.dumps(result._result)
            elif status == "unreachable":
                host_result.unreachable = json.dumps(result._result)
            elif status == "skipped":
                host_result.skipped = json.dumps(result._result)
            elif status == "success":
                host_result.success = json.dumps(result._result)
            else:
                logger.error("No such status(failed|unreachable|skipped|success), please check!")
            host_result.save()
        except Exception as e:
            logger.error("Save Ansible host result to database error!, %s" % e.message)

    @staticmethod
    def save_no_host_result(task):
        try:
            task = AnsibleTask.objects.get(uuid=task._uuid)
            host_result = AnsibleHostResult(task=task, no_host="no host to run this task")
            host_result.save()
        except Exception as e:
            logger.error("Save Ansible host result to database error!, %s" % e.message)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.save_task_result(result, "failed")
        host = result._host
        self.results[-1]['tasks'][-1]['failed'][host.name] = result._result

    def v2_runner_on_unreachable(self, result):
        self.save_task_result(result, "unreachable")
        host = result._host
        self.results[-1]['tasks'][-1]['unreachable'][host.name] = result._result

    def v2_runner_on_skipped(self, result):
        self.save_task_result(result, "skipped")
        host = result._host
        self.results[-1]['tasks'][-1]['skipped'][host.name] = result._result

    def v2_runner_on_no_hosts(self, task):
        self.save_no_host_result(task)
        self.results[-1]['tasks'][-1]['no_hosts']['msg'] = "no host to run this task"

    def v2_runner_on_ok(self, result):
        self.save_task_result(result, "success")
        host = result._host
        self.results[-1]['tasks'][-1]['success'][host.name] = result._result

    def v2_playbook_on_play_start(self, play):
        self.results.append(self._new_play(play))

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.results[-1]['tasks'].append(self._new_task(task))

    def v2_playbook_on_stats(self, stats):
        """AdHoc模式下这个钩子不会执行
        """
        hosts = sorted(stats.processed.keys())

        summary = {}
        for h in hosts:
            s = stats.summarize(h)
            summary[h] = s

        self.output['plays'] = self.results
        self.output['stats'] = summary
        print("summary: %s", summary)


class PlayBookRunner(object):
    """用于执行AnsiblePlaybook的接口.简化Playbook对象的使用.
    """

    def __init__(self, config, palybook_path, playbook_var,
                 become_pass, *hosts, **group_vars):
        """

        :param config: Config实例
        :param palybook_path: playbook的路径
        :param playbook_var: 执行Playbook时的变量
        :param become_pass: sudo passsword
        :param hosts: 可变位置参数, 为一个资产列表, 每一个资产用dict表示, 以下是这个dict必须包含的key
            [{
                        "name": "asset_name",
                        "ip": "asset_ip",
                        "port": "asset_port",
                        "username": "asset_user",
                        "password": "asset_pass",
                        "key": "asset_private_key",
                        "group": "asset_group_name",
                        ...
            }]
        :param group_vars: 可变关键字参数, 是资产组变量, 记录对应的资产组变量
                "groupName1": {"group_variable1": "value1",...}
                "groupName2": {"group_variable1": "value1",...}
        """

        self.options = config

        # 设置verbosity级别, 及命令行的--verbose选项
        self.display = Display()
        self.display.verbosity = self.options.verbosity
        playbook_executor.verbosity = self.options.verbosity

        # sudo成其他用户的配置
        self.options.become = True
        self.options.become_method = 'sudo'
        self.options.become_user = 'root'
        passwords = {'become_pass': become_pass}

        # 传入playbook的路径，以及执行需要的变量
        pb_dir = os.path.dirname(__file__)
        playbook = "%s/%s" % (pb_dir, palybook_path)

        # 生成Ansible inventory, 这些变量Mixin都会用到
        self.hosts = hosts
        self.group_vars = group_vars
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        self.groups = []
        self.variable_manager.extra_vars = playbook_var
        self.inventory = self.gen_inventory()

        # 初始化playbook的executor
        self.pbex = playbook_executor.PlaybookExecutor(
            playbooks=[playbook],
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=passwords)

    def run(self):
        """执行Playbook, 记录执行日志, 处理执行结果.
        :return: <AnsibleResult>对象
        """
        self.pbex.run()
        stats = self.pbex._tqm._stats

        # 测试执行是否成功
        run_success = True
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            if t['unreachable'] > 0 or t['failures'] > 0:
                run_success = False

        # TODO: 记录执行日志, 处理执行结果.

        return stats


class ADHocRunner(object):
    """
    ADHoc接口
    """
    def __init__(self,
                 hosts=C.DEFAULT_HOST_LIST,
                 module_name=C.DEFAULT_MODULE_NAME,  # * command
                 module_args=C.DEFAULT_MODULE_ARGS,  # * 'cmd args'
                 forks=C.DEFAULT_FORKS,  # 5
                 timeout=C.DEFAULT_TIMEOUT,  # SSH timeout = 10s
                 pattern="all",  # all
                 remote_user=C.DEFAULT_REMOTE_USER,  # root
                 module_path=None,  # dirs of custome modules
                 connection_type="smart",
                 become=None,
                 become_method=None,
                 become_user=None,
                 check=False,
                 passwords=None,
                 extra_vars=None,
                 private_key_file=None,
                 gather_facts='no'):

        self.pattern = pattern
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.module_name = module_name
        self.module_args = module_args
        self.check_module_args()
        self.gather_facts = gather_facts
        self.results_callback = BasicResultCallback()
        self.options = Options(
            connection=connection_type,
            timeout=timeout,
            module_path=module_path,
            forks=forks,
            become=become,
            become_method=become_method,
            become_user=become_user,
            check=check,
            remote_user=remote_user,
            extra_vars=extra_vars or [],
            private_key_file=private_key_file,
        )

        self.variable_manager.extra_vars = load_extra_vars(self.loader, options=self.options)
        self.variable_manager.options_vars = load_options_vars(self.options)
        self.passwords = passwords or {}
        self.inventory = JMSInventory(hosts)
        self.variable_manager.set_inventory(self.inventory)

        self.play_source = dict(
            name='Ansible Ad-hoc',
            hosts=self.pattern,
            gather_facts=self.gather_facts,
            tasks=[dict(action=dict(
                module=self.module_name,
                args=self.module_args
            ))]
        )

        self.play = Play().load(
            self.play_source,
            variable_manager=self.variable_manager,
            loader=self.loader,
        )

        self.runner = TaskQueueManager(
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=self.passwords,
            stdout_callback=self.results_callback,
        )

    def check_module_args(self):
        if self.module_name in C.MODULE_REQUIRE_ARGS and not self.module_args:
            err = "No argument passed to '%s' module." % self.module_name
            raise AnsibleError(err)

    def run(self):
        if not self.inventory.list_hosts("all"):
            raise AnsibleError("Inventory is empty.")

        if not self.inventory.list_hosts(self.pattern):
            raise AnsibleError(
                "pattern: %s  dose not match any hosts." % self.pattern)

        try:
            self.runner.run(self.play)
        except Exception as e:
            pass
        else:
            return self.results_callback.result_q
        finally:
            if self.runner:
                self.runner.cleanup()
            if self.loader:
                self.loader.cleanup_all_tmp_files()


def test_run():
    assets = [
        {
                "hostname": "192.168.152.129",
                "ip": "192.168.152.129",
                "port": 22,
                "username": "root",
                "password": "redhat",
        },
    ]
    hoc = ADHocRunner(module_name='shell', module_args='ls', hosts=assets)
    ret = hoc.run()
    print(ret)

if __name__ == "__main__":
    test_run()
