import os
import shutil
import yaml
from copy import deepcopy
from collections import defaultdict

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from common.utils import get_logger
from assets.automations.methods import platform_automation_methods
from ops.ansible import JMSInventory, PlaybookRunner, DefaultCallback

logger = get_logger(__name__)


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

    @property
    def runtime_dir(self):
        ansible_dir = settings.ANSIBLE_DIR
        path = os.path.join(
            ansible_dir, self.automation.type,
            self.automation.name.replace(' ', '_'),
            timezone.now().strftime('%Y%m%d_%H%M%S')
        )
        return path

    @property
    def inventory_path(self):
        return os.path.join(self.runtime_dir, 'inventory', 'hosts.json')

    @property
    def playbook_path(self):
        return os.path.join(self.runtime_dir, 'project', 'main.yml')

    def generate(self):
        self.prepare_playbook_dir()
        self.generate_inventory()
        self.generate_playbook()

    def prepare_playbook_dir(self):
        inventory_dir = os.path.dirname(self.inventory_path)
        playbook_dir = os.path.dirname(self.playbook_path)
        for d in [inventory_dir, playbook_dir]:
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True, mode=0o755)

    def host_callback(self, host, automation=None, **kwargs):
        enabled_attr = '{}_enabled'.format(self.__class__.method_type())
        method_attr = '{}_method'.format(self.__class__.method_type())

        method_enabled = automation and \
            getattr(automation, enabled_attr) and \
            getattr(automation, method_attr) and \
            getattr(automation, method_attr) in self.method_id_meta_mapper

        if not method_enabled:
            host['error'] = _('Change password disabled')
            return host

        self.method_hosts_mapper[getattr(automation, method_attr)].append(host['name'])
        return host

    def generate_inventory(self):
        inventory = JMSInventory(
            assets=self.automation.get_all_assets(),
            account_policy=self.ansible_account_policy,
            host_callback=self.host_callback
        )
        inventory.write_to_file(self.inventory_path)
        logger.debug("Generate inventory done: {}".format(self.inventory_path))

    def generate_playbook(self):
        main_playbook = []
        for method_id, host_names in self.method_hosts_mapper.items():
            method = self.method_id_meta_mapper.get(method_id)
            if not method:
                logger.error("Method not found: {}".format(method_id))
                continue
            method_playbook_dir_path = method['dir']
            method_playbook_dir_name = os.path.basename(method_playbook_dir_path)
            sub_playbook_dir = os.path.join(os.path.dirname(self.playbook_path), method_playbook_dir_name)
            sub_playbook_path = os.path.join(sub_playbook_dir, 'main.yml')
            shutil.copytree(method_playbook_dir_path, sub_playbook_dir)

            with open(sub_playbook_path, 'r') as f:
                host_playbook_play = yaml.safe_load(f)

            if isinstance(host_playbook_play, list):
                host_playbook_play = host_playbook_play[0]

            hosts_bulked = [host_names[i:i+self.bulk_size] for i in range(0, len(host_names), self.bulk_size)]
            for i, hosts in enumerate(hosts_bulked):
                plays = []
                play = deepcopy(host_playbook_play)
                play['hosts'] = ':'.join(hosts)
                plays.append(play)

                playbook_path = os.path.join(sub_playbook_dir, 'part_{}.yml'.format(i))
                with open(playbook_path, 'w') as f:
                    yaml.safe_dump(plays, f)
                self.playbooks.append([playbook_path, hosts])

                main_playbook.append({
                    'name': method['name'] + ' for part {}'.format(i),
                    'import_playbook': os.path.join(method_playbook_dir_name, 'part_{}.yml'.format(i))
                })

        with open(self.playbook_path, 'w') as f:
            yaml.safe_dump(main_playbook, f)

        logger.debug("Generate playbook done: " + self.playbook_path)

    def get_runners(self):
        runners = []
        for playbook_path in self.playbooks:
            runer = PlaybookRunner(
                self.inventory_path,
                playbook_path,
                self.runtime_dir,
                callback=PlaybookCallback(),
            )
            runners.append(runer)
        return runners

    def on_runner_done(self, runner, cb):
        raise NotImplementedError

    def on_runner_failed(self, runner, e):
        print("Runner failed: {} {}".format(e, self))

    def before_runner_start(self, runner):
        pass

    def run(self, **kwargs):
        self.generate()
        runners = self.get_runners()
        if len(runners) > 1:
            print("### 分批次执行开始任务, 总共 {}\n".format(len(runners)))
        else:
            print(">>> 开始执行任务\n")

        for i, runner in enumerate(runners, start=1):
            if len(runners) > 1:
                print(">>> 开始执行第 {} 批任务".format(i))
            self.before_runner_start(runner)
            try:
                cb = runner.run(**kwargs)
                self.on_runner_done(runner, cb)
            except Exception as e:
                self.on_runner_failed(runner, e)
            print('\n\n')
