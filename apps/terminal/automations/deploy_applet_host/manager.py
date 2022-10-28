import os
import datetime
import shutil
from django.conf import settings

from ops.ansible import PlaybookRunner, JMSInventory

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class DeployAppletHostManager:
    def __init__(self, applet_host):
        self.applet_host = applet_host
        self.run_dir = self.get_run_dir()

    @staticmethod
    def get_run_dir():
        base = os.path.join(settings.ANSIBLE_DIR, 'applet_host_deploy')
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        return os.path.join(base, now)

    def generate_playbook(self):
        playbook_src = os.path.join(CURRENT_DIR, 'playbook.yml')
        playbook_dir = os.path.join(self.run_dir, 'playbook')
        playbook_dst = os.path.join(playbook_dir, 'main.yml')
        os.makedirs(playbook_dir, exist_ok=True)
        shutil.copy(playbook_src, playbook_dst)
        return playbook_dst

    def generate_inventory(self):
        inventory = JMSInventory([self.applet_host], account_policy='privileged_only')
        inventory_dir = os.path.join(self.run_dir, 'inventory')
        inventory_path = os.path.join(inventory_dir, 'hosts.yml')
        inventory.write_to_file(inventory_path)
        return inventory_path

    def run(self, **kwargs):
        inventory = self.generate_inventory()
        playbook = self.generate_playbook()
        runner = PlaybookRunner(
            inventory=inventory, playbook=playbook, project_dir=self.run_dir
        )
        return runner.run(**kwargs)
