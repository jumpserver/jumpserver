import os
import datetime
import shutil

import yaml
from django.utils import timezone
from django.conf import settings

from common.utils import get_logger
from common.db.utils import safe_db_connection
from ops.ansible import PlaybookRunner, JMSInventory

logger = get_logger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class DeployAppletHostManager:
    def __init__(self, deployment):
        self.deployment = deployment
        self.run_dir = self.get_run_dir()

    @staticmethod
    def get_run_dir():
        base = os.path.join(settings.ANSIBLE_DIR, 'applet_host_deploy')
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        return os.path.join(base, now)

    def generate_playbook(self):
        playbook_src = os.path.join(CURRENT_DIR, 'playbook.yml')
        base_site_url = settings.BASE_SITE_URL
        bootstrap_token = settings.BOOTSTRAP_TOKEN
        host_id = str(self.deployment.host.id)
        if not base_site_url:
            base_site_url = "localhost:8080"
        with open(playbook_src) as f:
            plays = yaml.safe_load(f)
        for play in plays:
            play['vars'].update(self.deployment.host.deploy_options)
            play['vars']['DownloadHost'] = base_site_url + '/download/'
            play['vars']['CORE_HOST'] = base_site_url
            play['vars']['BOOTSTRAP_TOKEN'] = bootstrap_token
            play['vars']['HOST_ID'] = host_id
            play['vars']['HOST_NAME'] = self.deployment.host.name

        playbook_dir = os.path.join(self.run_dir, 'playbook')
        playbook_dst = os.path.join(playbook_dir, 'main.yml')
        os.makedirs(playbook_dir, exist_ok=True)
        with open(playbook_dst, 'w') as f:
            yaml.safe_dump(plays, f)
        return playbook_dst

    def generate_inventory(self):
        inventory = JMSInventory([self.deployment.host], account_policy='privileged_only')
        inventory_dir = os.path.join(self.run_dir, 'inventory')
        inventory_path = os.path.join(inventory_dir, 'hosts.yml')
        inventory.write_to_file(inventory_path)
        return inventory_path

    def _run(self, **kwargs):
        inventory = self.generate_inventory()
        playbook = self.generate_playbook()
        runner = PlaybookRunner(
            inventory=inventory, playbook=playbook, project_dir=self.run_dir
        )
        return runner.run(**kwargs)

    def run(self, **kwargs):
        try:
            self.deployment.date_start = timezone.now()
            cb = self._run(**kwargs)
            self.deployment.status = cb.status
        except Exception as e:
            logger.error("Error: {}".format(e))
            self.deployment.status = 'error'
        finally:
            self.deployment.date_finished = timezone.now()
            with safe_db_connection():
                self.deployment.save()
