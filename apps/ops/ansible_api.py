# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

import os
import json
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory, Host, Group
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor import playbook_executor
from ansible.utils.display import Display
from ansible.playbook.play import Play
import ansible.constants as default_config
from ansible.plugins.callback import CallbackBase


class AnsibleError(StandardError):
    pass


class Config(object):
    """Ansible运行时配置类, 用于初始化Ansible.
    """
    def __init__(self, verbosity=None, inventory=None, listhosts=None, subset=None, module_paths=None, extra_vars=None,
                 forks=None, ask_vault_pass=None, vault_password_files=None, new_vault_password_file=None,
                 output_file=None, tags=None, skip_tags=None, one_line=None, tree=None, ask_sudo_pass=None, ask_su_pass=None,
                 sudo=None, sudo_user=None, become=None, become_method=None, become_user=None, become_ask_pass=None,
                 ask_pass=None, private_key_file=None, remote_user=None, connection=None, timeout=None, ssh_common_args=None,
                 sftp_extra_args=None, scp_extra_args=None, ssh_extra_args=None, poll_interval=None, seconds=None, check=None,
                 syntax=None, diff=None, force_handlers=None, flush_cache=None, listtasks=None, listtags=None, module_path=None):
        self.verbosity = verbosity
        self.inventory = inventory
        self.listhosts = listhosts
        self.subset = subset
        self.module_paths = module_paths
        self.extra_vars = extra_vars
        self.forks = forks
        self.ask_vault_pass = ask_vault_pass
        self.vault_password_files = vault_password_files
        self.new_vault_password_file = new_vault_password_file
        self.output_file = output_file
        self.tags = tags
        self.skip_tags = skip_tags
        self.one_line = one_line
        self.tree = tree
        self.ask_sudo_pass = ask_sudo_pass
        self.ask_su_pass = ask_su_pass
        self.sudo = sudo
        self.sudo_user = sudo_user
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.become_ask_pass = become_ask_pass
        self.ask_pass = ask_pass
        self.private_key_file = private_key_file
        self.remote_user = remote_user
        self.connection = connection
        self.timeout = timeout
        self.ssh_common_args = ssh_common_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.ssh_extra_args = ssh_extra_args
        self.poll_interval = poll_interval
        self.seconds = seconds
        self.check = check
        self.syntax = syntax
        self.diff = diff
        self.force_handlers = force_handlers
        self.flush_cache = flush_cache
        self.listtasks = listtasks
        self.listtags = listtags
        self.module_path = module_path
        self.__overwrite_default()

    def __overwrite_default(self):
        """上面并不能包含Ansible所有的配置, 如果有其他的配置,
        可以通过替换default_config模块里面的变量进行重载，　
        比如 default_config.DEFAULT_ASK_PASS = False.
        """
        default_config.HOST_KEY_CHECKING = False


class InventoryMixin(object):
    """提供生成Ansible inventory对象的方法
    """

    def gen_inventory(self):
        """用于生成动态构建Ansible Inventory.

        :return: 返回一个Ansible的inventory对象
        """

        # TODO: 验证输入

        # 创建Ansible Group.
        for asset in self.hosts:
            g_name = asset.get('group', 'default')
            if g_name not in [g.name for g in self.groups]:
                group = Group(name=asset.get('group', 'default'))
                self.groups.append(group)

        # 初始化组变量
        for group_name, variables in self.group_vars.iteritems():
            for g in self.groups:
                if g.name == group_name:
                    for v_name, v_value in variables:
                        g.set_variable(v_name, v_value)

        # 往组里面添加Host
        for asset in self.hosts:
            host = Host(name=asset['name'], port=asset['port'])
            host.set_variable('ansible_ssh_host', asset['ip'])
            host.set_variable('ansible_ssh_port', asset['port'])
            host.set_variable('ansible_ssh_user', asset['username'])

            if asset.get('password'):
                host.set_variable('ansible_ssh_pass', asset['password'])
            if asset.get('key'):
                host.set_variable('ansible_ssh_private_key_file', asset['key'])

            for key, value in asset.iteritems():
                if key not in ["name", "port", "ip", "username", "password", "key"]:
                    host.set_variable(key, value)
            for g in self.groups:
                if g.name == asset.get('group', 'default'):
                    g.add_host(host)

        # 生成Ansible inventory对象
        inventory = Inventory(loader=self.loader, variable_manager=self.variable_manager, host_list=[])
        for g in self.groups:
            inventory.add_group(g)
        self.variable_manager.set_inventory(inventory)
        return inventory


class CallbackModule(CallbackBase):
    """处理和分析Ansible运行结果,并保存数据.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'json'

    def __init__(self, display=None):
        super(CallbackModule, self).__init__(display)
        self.results = []

    def _new_play(self, play):
        return {
            'play': {
                'name': play.name,
                'id': str(play._uuid)
            },
            'tasks': []
        }

    def _new_task(self, task):
        return {
            'task': {
                'name': task.name,
                'id': str(task._uuid)
            },
            'hosts': {}
        }

    def v2_playbook_on_play_start(self, play):
        self.results.append(self._new_play(play))

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.results[-1]['tasks'].append(self._new_task(task))

    def v2_runner_on_ok(self, result, **kwargs):
        host = result._host
        self.results[-1]['tasks'][-1]['hosts'][host.name] = result._result

    def v2_playbook_on_stats(self, stats):
        """Display info about playbook statistics"""

        hosts = sorted(stats.processed.keys())

        summary = {}
        for h in hosts:
            s = stats.summarize(h)
            summary[h] = s

        output = {
            'plays': self.results,
            'stats': summary
        }

        print(json.dumps(output, indent=4, sort_keys=True))

    v2_runner_on_failed = v2_runner_on_ok
    v2_runner_on_unreachable = v2_runner_on_ok
    v2_runner_on_skipped = v2_runner_on_ok


class PlayBookRunner(InventoryMixin):
    """用于执行AnsiblePlaybook的接口.简化Playbook对象的使用.
    """

    def __init__(self, config, palybook_path, playbook_var, become_pass, *hosts, **group_vars):
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


class ADHocRunner(InventoryMixin):
    """ADHoc接口
    """
    def __init__(self, config, play_data, become_pass=None, *hosts, **group_vars):
        """
        :param hosts: 见PlaybookRunner参数
        :param group_vars: 见PlaybookRunner参数
        :param config: Config实例

        :param play_data:
        play_data = dict(
            name="Ansible Ad-Hoc",
            hosts=pattern,
            gather_facts=True,
            tasks=[dict(action=dict(module='service', args={'name': 'vsftpd', 'state': 'restarted'}), async=async, poll=poll)]
        )
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
        self.passwords = {'become_pass': become_pass}

        # 生成Ansible inventory, 这些变量Mixin都会用到
        self.hosts = hosts
        self.group_vars = group_vars
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        self.groups = []
        self.inventory = self.gen_inventory()

        # 初始化callback插件
        self.results_callback = CallbackModule()

        self.play = Play().load(play_data, variable_manager=self.variable_manager, loader=self.loader)

    def run(self):
        """执行ADHoc 记录日志，　处理结果
        """
        tqm = None
        # TODO:日志和结果分析
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                stdout_callback=self.results_callback,
                options=self.options,
                passwords=self.passwords
            )
            ext_code = tqm.run(self.play)
            result = json.dumps(self.results_callback.results)
            return ext_code, result
        finally:
            if tqm:
                tqm.cleanup()


if __name__ == "__main__":
    conf = Config()
    assets = [{
                "name": "localhost",
                "ip": "localhost",
                "port": "22",
                "username": "yumaojun",
                "password": "yusky0902",
                "key": "asset_private_key",
    }]
    # 初始化Play
    play_source = {
            "name": "Ansible Play",
            "hosts": "*",
            "gather_facts": "no",
            "tasks": [
                dict(action=dict(module='setup')),
            ]
        }
    hoc = ADHocRunner(conf, play_source,'yusky0902', *assets)
    ext_code, result = hoc.run()
    print ext_code
    print result