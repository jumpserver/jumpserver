import datetime
import errno
import json
import os
import re
import shutil
import uuid
from pathlib import Path

import yaml
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.db.utils import safe_db_connection
from common.utils import get_logger
from ops.ansible import JMSInventory, SuperPlaybookRunner
from terminal.const import PublishStatus
from terminal.models import AppProvider, VirtualAppPublication
from terminal.utils.virtualapp import stage_image_archives

logger = get_logger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_manifest():
    path = Path(settings.DATA_DIR) / 'virtualapp' / 'manifest.json'
    try:
        with path.open() as stream:
            manifest = json.load(stream)
    except FileNotFoundError:
        return {}
    if not isinstance(manifest, dict):
        raise ValueError('Invalid virtual application offline manifest')
    for name in ('panda', 'docker'):
        if name in manifest and not isinstance(manifest[name], dict):
            raise ValueError(f'Invalid {name} offline resource')
        for key, value in manifest.get(name, {}).items():
            if key in ('image', 'architecture', 'image_id', 'file', 'sha256', 'version') and not isinstance(value, str):
                raise ValueError(f'Invalid {name} offline {key}')
    return manifest


def default_panda_image():
    try:
        return load_manifest().get('panda', {}).get('image') or f'jumpserver/panda:{settings.VERSION}'
    except (OSError, ValueError):
        # Keep form metadata readable. Deployment validation reports the
        # malformed local configuration, and staging must never ignore it.
        return ''


def stage_resources(run_dir, image):
    """Keep offline resources inside the directory already mounted into Ansible EE."""
    root = (Path(settings.DATA_DIR) / 'virtualapp').resolve()
    manifest = load_manifest()
    resources = {}
    for name in ('panda', 'docker'):
        resource = dict(manifest.get(name, {}))
        if not resource or (name == 'panda' and resource.get('image') != image):
            resources[name] = {}
            continue
        if not re.fullmatch(r'[a-f0-9]{64}', resource.get('sha256', '')):
            raise ValueError(f'Invalid {name} offline archive checksum')
        if not resource.get('architecture'):
            raise ValueError(f'Missing {name} offline architecture')
        if name == 'panda' and not re.fullmatch(r'sha256:[a-f0-9]{64}', resource.get('image_id', '')):
            raise ValueError('Invalid Panda offline image ID')
        files = {'file': resource.get('file', '')}
        if name == 'docker':
            files['service'] = 'docker.service'
        for key, relative in files.items():
            source = (root / relative).resolve()
            if not relative or Path(relative).is_absolute() or not source.is_relative_to(root):
                raise ValueError(f'Invalid {name} offline archive path')
            resource[key] = ''
            # Existing Docker/images remain usable with missing offline files.
            # Ansible only requires these files when installing from the bundle.
            if source.is_file():
                destination = Path(run_dir) / 'offline' / source.name
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                try:
                    try:
                        os.link(source, destination)
                    except OSError as exc:
                        if exc.errno != errno.EXDEV:
                            raise
                        shutil.copyfile(source, destination)
                except FileNotFoundError:
                    # Installer may remove an old archive after publishing its manifest.
                    if source.exists():
                        raise
                else:
                    resource[key] = str(destination)
        resources[name] = resource
    return resources


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
            [self.provider.host], account_policy='privileged_only',
            protocol='ssh', exclude_localhost=True,
            account_selector=lambda asset: self.provider.select_deploy_account(),
            host_callback=self.configure_ssh_host,
        )
        # A disabled provider must remain deployable during maintenance.
        # This explicit target also avoids JMSInventory's active-asset filter.
        inventory.assets = [self.provider.host]
        path = os.path.join(self.run_dir, 'inventory', 'hosts.yml')
        inventory.write_to_file(path)
        with open(path) as stream:
            hosts = json.load(stream)['all']['hosts']
        if len(hosts) != 1 or inventory.exclude_hosts:
            raise ValueError('No deployable SSH host: check the privileged account and platform automation')
        host = next(iter(hosts.values()))
        if host.get('ansible_connection') != 'ssh':
            raise ValueError('Application provider deployment requires SSH')
        return path

    @staticmethod
    def configure_ssh_host(host, account=None, **kwargs):
        if not account or host.get('error'):
            return host
        host['ansible_connection'] = 'ssh'
        if not account.su_from:
            host['ansible_become'] = account.username != 'root'
            if host['ansible_become']:
                host['ansible_become_method'] = 'sudo'
                host['ansible_become_user'] = 'root'
                if account.secret_type == 'password':
                    host['ansible_become_password'] = account.escape_jinja2_syntax(account.secret)
        return host

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

        if self.deployment.publication_id:
            app = self.deployment.publication.app
            variables = {
                'APP_IMAGE': app.image_name,
                'APP_IMAGE_RESOURCES': stage_image_archives(app, self.run_dir),
            }
        else:
            options = self.provider.deploy_options
            core_host = options.get('CORE_HOST') or settings.SITE_URL or ''
            variables = {
                **options,
                'CORE_HOST': core_host.rstrip('/'),
                'PANDA_IMAGE': options.get('PANDA_IMAGE') or default_panda_image(),
            }
            resources = stage_resources(self.run_dir, variables['PANDA_IMAGE'])
            variables['PANDA_RESOURCE'] = resources['panda']
            variables['DOCKER_RESOURCE'] = resources['docker']
            variables['PANDA_ACCESS_KEY'] = self.get_access_key()
            variables['PANDA_PROVIDER_ID'] = str(self.provider.id)
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
            if not self.deployment.publication_id:
                self.provider.deploy_options = self.provider.validate_deployment()
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
            result = runner.run(quiet=False, timeout=1800)
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
                    values.update(
                        app_version=app.version, date_synced=timezone.now(),
                    )
                # Panda may finish publishing while this SSH check runs.
                VirtualAppPublication.objects.filter(
                    pk=publication.pk, app__version=app.version, app__image_name=app.image_name,
                ).exclude(
                    status=PublishStatus.success, app_version=app.version,
                ).update(**values)
        except Exception as exc:
            logger.exception('Deploy app provider failed: %s', exc)
            self.deployment.status = 'error'
            if self.deployment.publication_id:
                publication = self.deployment.publication
                app = publication.app
                VirtualAppPublication.objects.filter(
                    pk=publication.pk, app__version=app.version, app__image_name=app.image_name,
                ).exclude(
                    status=PublishStatus.success, app_version=app.version,
                ).update(status=PublishStatus.failed, date_updated=timezone.now())
        finally:
            self.deployment.date_finished = timezone.now()
            with safe_db_connection():
                self.deployment.save(update_fields=['status', 'date_finished', 'date_updated'])
            if not settings.DEBUG_DEV:
                shutil.rmtree(self.run_dir, ignore_errors=True)
