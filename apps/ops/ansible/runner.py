# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

import os
from collections import namedtuple, defaultdict

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.vars import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.playbook.play import Play
import ansible.constants as C
from ansible.utils.vars import load_extra_vars
from ansible.utils.vars import load_options_vars

from .inventory import JMSInventory
from .callback import AdHocResultCallback, PlaybookResultCallBack, \
    CommandResultCallback
from common.utils import get_logger


__all__ = ["AdHocRunner", "PlayBookRunner"]

C.HOST_KEY_CHECKING = False

logger = get_logger(__name__)


# Jumpserver not use playbook
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


class AdHocRunner(object):
    """
    ADHoc接口
    """
    Options = namedtuple("Options", [
        'connection', 'module_path', 'private_key_file', "remote_user",
        'timeout', 'forks', 'become', 'become_method', 'become_user',
        'check', 'extra_vars',
        ]
    )

    results_callback_class = AdHocResultCallback

    def __init__(self,
                 hosts=C.DEFAULT_HOST_LIST,
                 forks=C.DEFAULT_FORKS,  # 5
                 timeout=C.DEFAULT_TIMEOUT,  # SSH timeout = 10s
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

        self.pattern = ''
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.gather_facts = gather_facts
        self.results_callback = AdHocRunner.results_callback_class()
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

        self.variable_manager.extra_vars = load_extra_vars(self.loader,
                                                           options=self.options)
        self.variable_manager.options_vars = load_options_vars(self.options)
        self.passwords = passwords or {}
        self.inventory = JMSInventory(hosts)
        self.variable_manager.set_inventory(self.inventory)
        self.tasks = []
        self.play_source = None
        self.play = None
        self.runner = None

    @staticmethod
    def check_module_args(module_name, module_args=''):
        if module_name in C.MODULE_REQUIRE_ARGS and not module_args:
            err = "No argument passed to '%s' module." % module_name
            print(err)
            return False
        return True

    def run(self, task_tuple, pattern='all', task_name='Ansible Ad-hoc'):
        """
        :param task_tuple:  (('shell', 'ls'), ('ping', ''))
        :param pattern:
        :param task_name:
        :return:
        """
        for module, args in task_tuple:
            if not self.check_module_args(module, args):
                return
            self.tasks.append(
                dict(action=dict(
                    module=module,
                    args=args,
                ))
            )

        self.play_source = dict(
            name=task_name,
            hosts=pattern,
            gather_facts=self.gather_facts,
            tasks=self.tasks
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
        """
        :return: {
            "success": ['hostname',],
            "failed": [('hostname', 'msg'), {}],
        }
        """
        result = {'success': [], 'failed': []}
        for host in self.results_callback.result_q['contacted']:
            result['success'].append(host)

        for host, msgs in self.results_callback.result_q['dark'].items():
            msg = '\n'.join(['{} {}: {}'.format(
                msg.get('module_stdout', ''),
                msg.get('invocation', {}).get('module_name'),
                msg.get('msg', '')) for msg in msgs])
            result['failed'].append((host, msg))
        return result


def test_run():
    assets = [
        {
                "hostname": "192.168.244.129",
                "ip": "192.168.244.129",
                "port": 22,
                "username": "root",
                "password": "redhat",
        },
    ]
    task_tuple = (('shell', 'ls'),)
    hoc = AdHocRunner(hosts=assets)
    hoc.results_callback = CommandResultCallback()
    ret = hoc.run(task_tuple)
    print(ret)

    #play = PlayBookRunner(assets, playbook_path='/tmp/some.yml')
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
    #play.run()


if __name__ == "__main__":
    test_run()
