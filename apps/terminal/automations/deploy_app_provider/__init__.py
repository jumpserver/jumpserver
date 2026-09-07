import datetime
import os
import shutil
import uuid

import yaml
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.db.utils import safe_db_connection
from common.utils import get_logger
from ops.ansible import JMSInventory, SuperPlaybookRunner
from terminal.const import PublishStatus
from terminal.models import AppProvider, VirtualAppPublication

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

    @transaction.atomic
    def get_access_key(self):
        from terminal.serializers import TerminalRegistrationSerializer

        provider = AppProvider.objects.select_for_update().get(pk=self.provider.pk)
        terminal = provider.terminal
        if terminal and terminal.type != 'panda':
            raise ValueError('Provider terminal must be Panda')
        if not terminal or not terminal.user:
            if terminal:
                provider.terminal = None
                provider.save(update_fields=['terminal', 'date_updated'])
            serializer = TerminalRegistrationSerializer(data={
                'name': f'[Panda]-{provider.id}',
                'type': 'panda',
                'provider_id': provider.id,
            })
            serializer.is_valid(raise_exception=True)
            terminal = serializer.save()
        access_key = terminal.user.access_keys.filter(is_active=True).first()
        if not access_key:
            access_key = terminal.user.create_access_key()
        return access_key.get_full_value()

    def generate_playbook(self):
        template = 'publish.yml' if self.deployment.publication_id else 'playbook.yml'
        with open(os.path.join(CURRENT_DIR, template)) as f:
            plays = yaml.safe_load(f)

        options = self.provider.deploy_options
        core_host = options.get('CORE_HOST') or settings.SITE_URL or 'http://localhost:8080'
        variables = {
            **options,
            'CORE_HOST': core_host.rstrip('/'),
            'PANDA_HOST_IP': self.provider.host.address,
            'PANDA_IMAGE': options.get('PANDA_IMAGE', 'jumpserver/panda:latest'),
            'PANDA_RANGE_PORTS': options.get('PANDA_RANGE_PORTS', '6900-7900'),
            'IGNORE_VERIFY_CERTS': options.get('IGNORE_VERIFY_CERTS', True),
        }
        if self.deployment.publication_id:
            variables['APP_IMAGE'] = self.deployment.publication.app.image_name
        else:
            variables['PANDA_ACCESS_KEY'] = self.get_access_key()
        for play in plays:
            play['vars'].update(variables)

        path = os.path.join(self.run_dir, 'playbook', 'main.yml')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            os.chmod(path, 0o600)
            yaml.safe_dump(plays, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return path

    def run(self):
        try:
            self.deployment.date_start = timezone.now()
            self.deployment.status = 'running'
            self.deployment.save(update_fields=['date_start', 'status', 'date_updated'])
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
            self.deployment.status = 'success' if result.status == 'successful' else result.status
            if self.deployment.publication_id:
                publication = self.deployment.publication
                app = publication.app
                success = self.deployment.status == 'success'
                values = {
                    'status': PublishStatus.success if success else PublishStatus.failed,
                    'date_updated': timezone.now(),
                }
                if success:
                    values.update(app_version=app.version, image_digest='', date_synced=timezone.now())
                VirtualAppPublication.objects.filter(
                    pk=publication.pk, app__version=app.version, app__image_name=app.image_name,
                ).update(**values)
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
