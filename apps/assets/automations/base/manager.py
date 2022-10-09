import os

from django.conf import settings
from django.utils import timezone

from ops.ansible import JMSInventory


class BasePlaybookManager:
    ansible_account_policy = 'privileged_first'

    def __init__(self, execution):
        self.execution = execution
        self.automation = execution.automation

    def get_grouped_assets(self):
        return self.automation.all_assets_group_by_platform()

    @property
    def playbook_dir_path(self):
        ansible_dir = settings.ANSIBLE_DIR
        path = os.path.join(
            ansible_dir, self.automation.type, self.automation.name,
            timezone.now().strftime('%Y%m%d_%H%M%S')
        )
        return path

    @property
    def inventory_path(self):
        return os.path.join(self.playbook_dir_path, 'inventory', 'hosts.json')

    @property
    def playbook_path(self):
        return os.path.join(self.playbook_dir_path, 'project', 'main.yml')

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

    def inventory_kwargs(self):
        raise NotImplemented

    def generate_inventory(self):
        inventory = JMSInventory(
            assets=self.automation.get_all_assets(),
            account_policy=self.ansible_account_policy,
            **self.inventory_kwargs()
        )
        inventory.write_to_file(self.inventory_path)
        print("Generate inventory done: {}".format(self.inventory_path))

    def generate_playbook(self):
        raise NotImplemented

    def get_runner(self):
        raise NotImplemented

    def run(self, **kwargs):
        self.generate()
        runner = self.get_runner()
        return runner.run(**kwargs)

