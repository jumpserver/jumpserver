import datetime
import os
import shutil
import uuid

import yaml
from django.conf import settings
from django.utils import timezone

from common.db.utils import safe_db_connection
from common.utils import get_logger
from ops.ansible import JMSInventory, SuperPlaybookRunner

logger = get_logger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class DeployAppProviderManager:
    def __init__(self, deployment):
        self.deployment = deployment
        self.provider = deployment.provider
        self.run_dir = self.get_run_dir()

    @staticmethod
    def get_run_dir():
        base = os.path.join(settings.ANSIBLE_DIR, 'app_provider_deploy')
        now = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        return os.path.join(base, f'{now}_{uuid.uuid4().hex[:8]}')

    def generate_inventory(self):
        inventory = JMSInventory(
            [self.provider.host], account_policy='privileged_only'
        )
        path = os.path.join(self.run_dir, 'inventory', 'hosts.yml')
        inventory.write_to_file(path)
        return path

    def generate_playbook(self):
        template = 'publish.yml' if self.deployment.publication_id else 'playbook.yml'
        with open(os.path.join(CURRENT_DIR, template)) as f:
            plays = yaml.safe_load(f)

        options = self.provider.deploy_options
        core_host = options.get('CORE_HOST') or settings.SITE_URL or 'http://localhost:8080'
        variables = {
            **options,
            'CORE_HOST': core_host.rstrip('/'),
            'BOOTSTRAP_TOKEN': settings.BOOTSTRAP_TOKEN,
            'PROVIDER_ID': str(self.provider.id),
            'PROVIDER_NAME': self.provider.name,
            'PANDA_HOST_IP': self.provider.host.address,
            'PANDA_IMAGE': options.get('PANDA_IMAGE', 'jumpserver/panda:latest'),
            'PANDA_RANGE_PORTS': options.get('PANDA_RANGE_PORTS', '6900-7900'),
            'IGNORE_VERIFY_CERTS': options.get('IGNORE_VERIFY_CERTS', True),
        }
        if self.deployment.publication_id:
            variables['APP_IMAGE'] = self.deployment.publication.app.image_name
        for play in plays:
            play['vars'].update(variables)

        path = os.path.join(self.run_dir, 'playbook', 'main.yml')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            yaml.safe_dump(plays, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return path

    def run(self):
        try:
            self.deployment.date_start = timezone.now()
            runner = SuperPlaybookRunner(
                inventory=self.generate_inventory(),
                playbook=self.generate_playbook(),
                project_dir=self.run_dir,
                safety_mode='playbook_unsafe',
                inventory_safety='json_escape',
            )
            # Provider deployments are user-triggered and their Celery task log
            # is the primary place to follow progress. Keep Ansible's normal
            # PLAY/TASK/RECAP output visible without enabling debug verbosity.
            result = runner.run(quiet=False)
            self.deployment.status = result.status
            if self.deployment.publication_id:
                publication_status = (
                    'pending' if result.status in ('success', 'successful') else 'failed'
                )
                self.deployment.publication.status = publication_status
                self.deployment.publication.save(update_fields=['status', 'date_updated'])
        except Exception as exc:
            logger.exception('Deploy app provider failed: %s', exc)
            self.deployment.status = 'error'
            if self.deployment.publication_id:
                self.deployment.publication.status = 'failed'
                self.deployment.publication.save(update_fields=['status', 'date_updated'])
        finally:
            self.deployment.date_finished = timezone.now()
            with safe_db_connection():
                self.deployment.save()
            if not settings.DEBUG_DEV:
                shutil.rmtree(self.run_dir, ignore_errors=True)
