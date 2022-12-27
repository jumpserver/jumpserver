import os
import shutil
from collections import defaultdict
from copy import deepcopy
from hashlib import md5
from socket import gethostname

import yaml
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from assets.automations.methods import platform_automation_methods
from assets.const import SecretType
from common.utils import get_logger, lazyproperty
from common.utils import ssh_pubkey_gen, ssh_key_string_to_obj
from ops.ansible import JMSInventory, PlaybookRunner, DefaultCallback

logger = get_logger(__name__)


class PushOrVerifyHostCallbackMixin:
    execution: callable
    host_account_mapper: dict
    ignore_account: bool
    need_privilege_account: bool
    generate_public_key: callable
    generate_private_key_path: callable

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(host, asset=asset, account=account, automation=automation, **kwargs)
        if host.get('error'):
            return host

        accounts = asset.accounts.all()
        if self.need_privilege_account and accounts.count() > 1 and account:
            accounts = accounts.exclude(id=account.id)

        if '*' not in self.execution.snapshot['accounts']:
            accounts = accounts.filter(username__in=self.execution.snapshot['accounts'])

        inventory_hosts = []
        for account in accounts:
            h = deepcopy(host)
            h['name'] += '_' + account.username
            self.host_account_mapper[h['name']] = account
            secret = account.secret

            private_key_path = None
            if account.secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(secret, path_dir)
                secret = self.generate_public_key(secret)

            h['secret_type'] = account.secret_type
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': secret,
                'private_key_path': private_key_path
            }
            inventory_hosts.append(h)
        return inventory_hosts


class PlaybookCallback(DefaultCallback):
    def playbook_on_stats(self, event_data, **kwargs):
        super().playbook_on_stats(event_data, **kwargs)


class BasePlaybookManager:
    bulk_size = 100
    ansible_account_policy = 'privileged_first'

    def __init__(self, execution):
        self.execution = execution
        self.automation = execution.automation
        self.method_id_meta_mapper = {
            method['id']: method
            for method in platform_automation_methods
            if method['method'] == self.__class__.method_type()
        }
        # 根据执行方式就行分组, 不同资产的改密、推送等操作可能会使用不同的执行方式
        # 然后根据执行方式分组, 再根据 bulk_size 分组, 生成不同的 playbook
        # 避免一个 playbook 中包含太多的主机
        self.method_hosts_mapper = defaultdict(list)
        self.playbooks = []

    @classmethod
    def method_type(cls):
        raise NotImplementedError

    def get_assets_group_by_platform(self):
        return self.automation.all_assets_group_by_platform()

    @lazyproperty
    def runtime_dir(self):
        ansible_dir = settings.ANSIBLE_DIR
        dir_name = '{}_{}'.format(self.automation.name.replace(' ', '_'), self.execution.id)
        path = os.path.join(
            ansible_dir, 'automations', self.execution.snapshot['type'],
            dir_name, timezone.now().strftime('%Y%m%d_%H%M%S')
        )
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True, mode=0o755)
        return path

    def host_callback(self, host, automation=None, **kwargs):
        enabled_attr = '{}_enabled'.format(self.__class__.method_type())
        method_attr = '{}_method'.format(self.__class__.method_type())

        method_enabled = automation and \
                         getattr(automation, enabled_attr) and \
                         getattr(automation, method_attr) and \
                         getattr(automation, method_attr) in self.method_id_meta_mapper

        if not method_enabled:
            host['error'] = _('{} disabled'.format(self.__class__.method_type()))
            return host
        return host

    @staticmethod
    def generate_public_key(private_key):
        return ssh_pubkey_gen(private_key=private_key, hostname=gethostname())

    @staticmethod
    def generate_private_key_path(secret, path_dir):
        key_name = '.' + md5(secret.encode('utf-8')).hexdigest()
        key_path = os.path.join(path_dir, key_name)

        if not os.path.exists(key_path):
            ssh_key_string_to_obj(secret, password=None).write_private_key_file(key_path)
            os.chmod(key_path, 0o400)
        return key_path

    def generate_inventory(self, platformed_assets, inventory_path):
        inventory = JMSInventory(
            assets=platformed_assets,
            account_policy=self.ansible_account_policy,
            host_callback=self.host_callback,
        )
        inventory.write_to_file(inventory_path)

    def generate_playbook(self, platformed_assets, platform, sub_playbook_dir):
        method_id = getattr(platform.automation, '{}_method'.format(self.__class__.method_type()))
        method = self.method_id_meta_mapper.get(method_id)
        if not method:
            logger.error("Method not found: {}".format(method_id))
            return method
        method_playbook_dir_path = method['dir']
        sub_playbook_path = os.path.join(sub_playbook_dir, 'project', 'main.yml')
        shutil.copytree(method_playbook_dir_path, os.path.dirname(sub_playbook_path))

        with open(sub_playbook_path, 'r') as f:
            plays = yaml.safe_load(f)
        for play in plays:
            play['hosts'] = 'all'

        with open(sub_playbook_path, 'w') as f:
            yaml.safe_dump(plays, f)
        return sub_playbook_path

    def get_runners(self):
        runners = []
        for platform, assets in self.get_assets_group_by_platform().items():
            assets_bulked = [assets[i:i + self.bulk_size] for i in range(0, len(assets), self.bulk_size)]

            for i, _assets in enumerate(assets_bulked, start=1):
                sub_dir = '{}_{}'.format(platform.name, i)
                playbook_dir = os.path.join(self.runtime_dir, sub_dir)
                inventory_path = os.path.join(self.runtime_dir, sub_dir, 'hosts.json')
                self.generate_inventory(_assets, inventory_path)
                playbook_path = self.generate_playbook(_assets, platform, playbook_dir)

                runer = PlaybookRunner(
                    inventory_path,
                    playbook_path,
                    self.runtime_dir,
                    callback=PlaybookCallback(),
                )
                runners.append(runer)
        return runners

    def on_host_success(self, host, result):
        pass

    def on_host_error(self, host, error, result):
        pass

    def on_runner_success(self, runner, cb):
        summary = cb.summary
        for state, hosts in summary.items():
            for host in hosts:
                result = cb.host_results.get(host)
                if state == 'ok':
                    self.on_host_success(host, result)
                elif state == 'skipped':
                    # TODO
                    print('skipped: ', hosts)
                else:
                    error = hosts.get(host)
                    self.on_host_error(host, error, result)

    def on_runner_failed(self, runner, e):
        print("Runner failed: {} {}".format(e, self))

    def before_runner_start(self, runner):
        print("Start run task: ")
        print("  inventory: {}".format(runner.inventory))
        print("  playbook: {}".format(runner.playbook))

    def run(self, *args, **kwargs):
        runners = self.get_runners()
        if len(runners) > 1:
            print("### 分批次执行开始任务, 总共 {}\n".format(len(runners)))
        else:
            print(">>> 开始执行任务\n")

        self.execution.date_start = timezone.now()
        for i, runner in enumerate(runners, start=1):
            if len(runners) > 1:
                print(">>> 开始执行第 {} 批任务".format(i))
            self.before_runner_start(runner)
            try:
                cb = runner.run(**kwargs)
                self.on_runner_success(runner, cb)
            except Exception as e:
                self.on_runner_failed(runner, e)
            print('\n')
        self.execution.status = 'success'
        self.execution.date_finished = timezone.now()
        self.execution.save()
