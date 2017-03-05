# ~*~ coding: utf-8 ~*~
# from __future__ import unicode_literals, print_function

import os
import logging
from collections import namedtuple

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
import ansible.constants as C
from ansible.utils.vars import load_extra_vars
from ansible.utils.vars import load_options_vars

from .inventory import JMSInventory
from common.utils import get_logger


__all__ = ["ADHocRunner", "Options"]

C.HOST_KEY_CHECKING = False

logger = get_logger(__name__)


class AnsibleError(StandardError):
    pass


class AdHocResultCallback(CallbackBase):
    """
    Custom Callback
    """
    def __init__(self, display=None):
        self.result_q = dict(contacted={}, dark={})
        super(AdHocResultCallback, self).__init__(display)

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


class PlaybookResultCallBack(CallbackBase):
    """
    Custom callback model for handlering the output data of
    execute playbook file,
    Base on the build-in callback plugins of ansible which named `json`.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'Dict'

    def __init__(self, display=None):
        super(PlaybookResultCallBack, self).__init__(display)
        self.results = []
        self.output = ""
        self.item_results = {}  # {"host": []}

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
                'name': task.get_name(),
            },
            'hosts': {}
        }

    def v2_playbook_on_no_hosts_matched(self):
        self.output = "skipping: No match hosts."

    def v2_playbook_on_no_hosts_remaining(self):
        pass

    def v2_playbook_on_task_start(self, task, is_conditional):
        self.results[-1]['tasks'].append(self._new_task(task))

    def v2_playbook_on_play_start(self, play):
        self.results.append(self._new_play(play))

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        summary = {}
        for h in hosts:
            s = stats.summarize(h)
            summary[h] = s

        if self.output:
            pass
        else:
            self.output = {
                'plays': self.results,
                'stats': summary
            }

    def gather_result(self, res):
        if res._task.loop and "results" in res._result and res._host.name in self.item_results:
            res._result.update({"results": self.item_results[res._host.name]})
            del self.item_results[res._host.name]

        self.results[-1]['tasks'][-1]['hosts'][res._host.name] = res._result

    def v2_runner_on_ok(self, res, **kwargs):
        if "ansible_facts" in res._result:
            del res._result["ansible_facts"]

        self.gather_result(res)

    def v2_runner_on_failed(self, res, **kwargs):
        self.gather_result(res)

    def v2_runner_on_unreachable(self, res, **kwargs):
        self.gather_result(res)

    def v2_runner_on_skipped(self, res, **kwargs):
        self.gather_result(res)

    def gather_item_result(self, res):
        self.item_results.setdefault(res._host.name, []).append(res._result)

    def v2_runner_item_on_ok(self, res):
        self.gather_item_result(res)

    def v2_runner_item_on_failed(self, res):
        self.gather_item_result(res)

    def v2_runner_item_on_skipped(self, res):
        self.gather_item_result(res)


class PlayBookRunner(object):
    """
    用于执行AnsiblePlaybook的接口.简化Playbook对象的使用.
    """
    Options = namedtuple('Options', [
        'listtags', 'listtasks', 'listhosts', 'syntax', 'connection',
        'module_path', 'forks', 'remote_user', 'private_key_file', 'timeout',
        'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
        'scp_extra_args', 'become', 'become_method', 'become_user',
        'verbosity', 'check', 'extra_vars'])

    def __init__(self,
                 hosts=None,
                 playbook_path=None,
                 forks=C.DEFAULT_FORKS,
                 listtags=False,
                 listtasks=False,
                 listhosts=False,
                 syntax=False,
                 module_path=None,
                 remote_user='root',
                 timeout=C.DEFAULT_TIMEOUT,
                 ssh_common_args=None,
                 ssh_extra_args=None,
                 sftp_extra_args=None,
                 scp_extra_args=None,
                 become=True,
                 become_method=None,
                 become_user="root",
                 verbosity=None,
                 extra_vars=None,
                 connection_type="ssh",
                 passwords=None,
                 private_key_file=None,
                 check=False):

        C.RETRY_FILES_ENABLED = False
        self.callbackmodule = PlaybookResultCallBack()
        if playbook_path is None or not os.path.exists(playbook_path):
            raise AnsibleError(
                "Not Found the playbook file: %s." % playbook_path)
        self.playbook_path = playbook_path
        self.loader = DataLoader()
        self.variable_manager = VariableManager()
        self.passwords = passwords or {}
        self.inventory = JMSInventory(hosts)

        self.options = self.Options(
            listtags=listtags,
            listtasks=listtasks,
            listhosts=listhosts,
            syntax=syntax,
            timeout=timeout,
            connection=connection_type,
            module_path=module_path,
            forks=forks,
            remote_user=remote_user,
            private_key_file=private_key_file,
            ssh_common_args=ssh_common_args or "",
            ssh_extra_args=ssh_extra_args or "",
            sftp_extra_args=sftp_extra_args,
            scp_extra_args=scp_extra_args,
            become=become,
            become_method=become_method,
            become_user=become_user,
            verbosity=verbosity,
            extra_vars=extra_vars or [],
            check=check
        )

        self.variable_manager.extra_vars = load_extra_vars(loader=self.loader,
                                                           options=self.options)
        self.variable_manager.options_vars = load_options_vars(self.options)

        self.variable_manager.set_inventory(self.inventory)

        # 初始化playbook的executor
        self.runner = PlaybookExecutor(
            playbooks=[self.playbook_path],
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=self.passwords)

        if self.runner._tqm:
            self.runner._tqm._stdout_callback = self.callbackmodule

    def run(self):
        if not self.inventory.list_hosts('all'):
            raise AnsibleError('Inventory is empty')
        self.runner.run()
        self.runner._tqm.cleanup()
        return self.callbackmodule.output


class ADHocRunner(object):
    """
    ADHoc接口
    """
    Options = namedtuple("Options", [
        'connection', 'module_path', 'private_key_file', "remote_user",
        'timeout', 'forks', 'become', 'become_method', 'become_user',
        'check', 'extra_vars',
        ]
    )

    def __init__(self,
                 hosts=C.DEFAULT_HOST_LIST,
                 task_name='Ansible Ad-hoc',
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
        self.results_callback = AdHocResultCallback()
        self.options = self.Options(
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
            name=task_name,
            hosts=self.pattern,
            gather_facts=self.gather_facts,
            tasks=[
                dict(action=dict(
                        module=self.module_name,
                        args=self.module_args,
                    )
                )
            ]
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
            logger.warning(e)
        else:
            logger.debug(self.results_callback.result_q)
            return self.results_callback.result_q
        finally:
            if self.runner:
                self.runner.cleanup()
            if self.loader:
                self.loader.cleanup_all_tmp_files()

    def clean_result(self):
        failed = self.results_callback.result_q['dark'].keys()
        success = self.results_callback.result_q['contacted'].keys()
        return {'failed': failed, 'success': success}


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

    play = PlayBookRunner(assets, playbook_path='/tmp/some.yml')
    """
    # /tmp/some.yml
    ---
    - name: Test the plabybook API.
      hosts: all
      remote_user: root
      gather_facts: yes
      tasks:
       - name: exec uptime
         shell: uptime
    """
    play.run()


if __name__ == "__main__":
    test_run()
