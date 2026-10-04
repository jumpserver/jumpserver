import datetime
import os
import re
import shutil
import time
import uuid
from functools import partial

import yaml
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.db.utils import safe_db_connection
from common.utils import get_logger, random_string
from ops.ansible import SuperPlaybookRunner, JMSInventory
from terminal.const import TINKER_TARGET_VERSION
from terminal.models import Applet, AppletHost, AppletHostDeployment, Terminal
from terminal.utils.tinker import parse_tinker_version

logger = get_logger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class DeployAppletHostManager:
    def __init__(self, deployment: AppletHostDeployment, applet: Applet = None,
                 install_applets: bool = True, **kwargs):
        self.deployment = deployment
        self.applet = applet
        self.run_dir = self.get_run_dir()
        self.install_applets = bool(install_applets)

    @staticmethod
    def get_run_dir():
        base = os.path.join(settings.ANSIBLE_DIR, "applet_host_deploy")
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:8]
        return os.path.join(base, f"{now}_{suffix}")

    def run(self, **kwargs):
        self._run(self._run_initial_deploy, **kwargs)

    def install_applet(self, **kwargs):
        self._run(self._run_install_applet, **kwargs)

    def uninstall_applet(self, **kwargs):
        self._run(self._run_uninstall_applet, **kwargs)

    def _run_initial_deploy(self, **kwargs):
        # Keep the old component identity until Windows has accepted and
        # completed full reinstallation, including any required reboot. Download
        # or installer failure must not replace the Core component identity.
        for phase in ('prepare', 'install'):
            logger.info('Tinker deployment phase: %s', phase)
            result = self._run_playbook(self.generate_initial_playbook, tags=phase, **kwargs)
            if result.status != 'success':
                return result

        credentials = self.create_tinker_credentials()
        startup_after = timezone.now()
        logger.info('Tinker deployment phase: configure and start')
        startup_verified = False
        try:
            # The runner removes its workspace after each phase.
            deployed = self._run_playbook(
                partial(self.generate_initial_playbook, credentials=credentials), tags='deploy', **kwargs,
            )
            if deployed.status != 'success':
                return deployed
            self.verify_tinker_startup(startup_after)
            startup_verified = True
        finally:
            if not startup_verified:
                self.discard_unconfirmed_terminal()
        self.retire_replaced_terminal()
        logger.info('Tinker deployment completed; new component startup and target version verified')
        if self.install_applets:
            logger.info('Tinker deployment phase: install remote applications')
            applets = self._run_playbook(self.generate_install_all_playbook, **kwargs)
            if applets.status != 'success':
                logger.error('Tinker deployment succeeded, but remote application installation failed. '
                             'Retry the failed applications from the existing application deployment action.')
            return applets
        return deployed

    def verify_tinker_startup(self, startup_after):
        host = self.deployment.host
        for attempt in range(10):
            host.refresh_from_db(fields=['terminal', 'tinker_version', 'date_synced'])
            if (host.terminal_id == self._expected_terminal_id
                    and host.date_synced and host.date_synced >= startup_after
                    and parse_tinker_version(host.tinker_version) == parse_tinker_version(TINKER_TARGET_VERSION)):
                return
            if attempt < 9:
                time.sleep(1)
        raise RuntimeError(
            f'Tinker did not send a fresh startup report for target version {TINKER_TARGET_VERSION}; '
            f'reported version: {host.tinker_version or "unknown"}. '
            'Check the applet host and redeploy.'
        )

    def create_tinker_credentials(self):
        from terminal.serializers import TerminalRegistrationSerializer

        # Administrator-initiated deployment creates the component locally;
        # public registration permissions and bootstrap tokens do not apply.
        with transaction.atomic():
            host = AppletHost.objects.select_for_update().get(pk=self.deployment.host.pk)
            old_terminal = host.terminal
            if old_terminal and old_terminal.type != 'tinker':
                raise ValueError('Applet host terminal must be Tinker')
            name = re.sub(r'\W', '_', host.name, flags=re.UNICODE)[:100]
            serializer = TerminalRegistrationSerializer(data={
                'name': f'[Tinker]-{name}-{random_string(7)}',
                'type': 'tinker',
                'comment': 'tinker',
            })
            serializer.is_valid(raise_exception=True)
            terminal = serializer.save()
            key = terminal.user.access_key
            if not key or not key.is_active:
                raise RuntimeError('Tinker component has no active access key')
            credentials = {'name': terminal.name, 'access_key': key.get_full_value()}
            host.terminal = terminal
            host.tinker_version = ''
            host.date_synced = None
            host.save(update_fields=['terminal', 'tinker_version', 'date_synced'])
            self._expected_terminal_id = terminal.pk
            self._retire_terminal_id = old_terminal.pk if old_terminal else None
            logger.info('Created a Tinker component identity; previous identity retained until startup succeeds')
        return credentials

    def discard_unconfirmed_terminal(self):
        # A failed attempt must not leave another usable component/key behind.
        # Restore only the Core binding, never the old Windows configuration or
        # a stale version report. The next full reinstall creates a new identity.
        with transaction.atomic():
            host = AppletHost.objects.select_for_update().get(pk=self.deployment.host.pk)
            if host.terminal_id != self._expected_terminal_id:
                raise RuntimeError('Tinker component binding changed during deployment')
            host.terminal_id = self._retire_terminal_id
            host.tinker_version = ''
            host.date_synced = None
            host.save(update_fields=['terminal', 'tinker_version', 'date_synced'])
            terminal = Terminal.objects.get(pk=self._expected_terminal_id)
            if not terminal.user or not terminal.user.is_service_account:
                raise RuntimeError('Unconfirmed Tinker component is not a service account')
            terminal.delete()
        logger.info('Discarded the unconfirmed Tinker component and key; retry full reinstallation')

    def retire_replaced_terminal(self):
        previous_id = getattr(self, '_retire_terminal_id', None)
        if not previous_id:
            return
        with transaction.atomic():
            host = AppletHost.objects.select_for_update().get(pk=self.deployment.host.pk)
            if host.terminal_id != self._expected_terminal_id:
                raise RuntimeError('Tinker component binding changed during deployment')
            previous = Terminal.objects.filter(pk=previous_id).first()
            if previous and previous.user and not previous.user.is_service_account:
                # Terminal.delete() also deletes its user. Never remove an ordinary
                # user while repairing an incorrectly bound component identity.
                logger.warning('Retaining the replaced Tinker identity because its user is not a service account')
                return
            if previous and not AppletHost.objects.filter(terminal=previous).exists():
                previous.delete()
        self._retire_terminal_id = None

    def _run_install_applet(self, **kwargs):
        if self.applet:
            generate_playbook = self.generate_install_applet_playbook
        else:
            generate_playbook = self.generate_install_all_playbook
        return self._run_playbook(generate_playbook, **kwargs)

    def _run_uninstall_applet(self, **kwargs):
        if self.applet:
            generate_playbook = self.generate_uninstall_applet_playbook
        else:
            raise ValueError("applet is required for uninstall_applet")
        return self._run_playbook(generate_playbook, **kwargs)

    def generate_initial_playbook(self, credentials=None):
        from terminal.serializers.applet_host import DeployOptionsSerializer

        site_url = settings.SITE_URL
        download_host = settings.APPLET_DOWNLOAD_HOST
        host_id = str(self.deployment.host.id)
        if not site_url:
            site_url = "http://localhost:8080"
        options = dict(self.deployment.host.deploy_options)
        options.setdefault('CORE_HOST', site_url)
        serializer = DeployOptionsSerializer(data=options)
        serializer.is_valid(raise_exception=True)
        options = serializer.validated_data
        core_host = options.get("CORE_HOST", site_url)
        core_host = core_host.rstrip("/")
        if not download_host:
            download_host = core_host
        download_host = download_host.rstrip("/")

        def handler(plays):
            for play in plays:
                play["vars"].update(options)
                play["vars"]["APPLET_DOWNLOAD_HOST"] = download_host
                play["vars"]["CORE_HOST"] = core_host
                play["vars"]["HOST_ID"] = host_id
                play["vars"]["DEPLOYMENT_ID"] = str(self.deployment.id)
                play["vars"]["INSTALL_APPLETS"] = self.install_applets
                play["vars"]["TINKER_VERSION"] = TINKER_TARGET_VERSION
                if credentials is not None:
                    play["vars"]["HOST_NAME"] = credentials['name']
                    play["vars"]["TINKER_ACCESS_KEY"] = credentials['access_key']
            return plays

        return self._generate_playbook("playbook.yml", handler)

    def generate_install_all_playbook(self):
        return self._generate_playbook("install_all.yml")

    def generate_install_applet_playbook(self):
        applet_name = self.applet.name

        def handler(plays):
            for play in plays:
                play["vars"]["applet_name"] = applet_name
            return plays

        return self._generate_playbook("install_applet.yml", handler)

    def generate_uninstall_applet_playbook(self):
        applet_name = self.applet.name

        def handler(plays):
            for play in plays:
                play["vars"]["applet_name"] = applet_name
            return plays

        return self._generate_playbook("uninstall_applet.yml", handler)

    def generate_inventory(self):
        inventory = JMSInventory(
            [self.deployment.host], account_policy="privileged_only",
            exclude_localhost=True,
        )
        inventory_dir = os.path.join(self.run_dir, "inventory")
        inventory_path = os.path.join(inventory_dir, "hosts.yml")
        inventory.write_to_file(inventory_path)
        return inventory_path

    def _generate_playbook(self, playbook_template_name, plays_handler: callable = None):
        playbook_src = os.path.join(CURRENT_DIR, playbook_template_name)
        with open(playbook_src) as f:
            plays = yaml.safe_load(f)
        if plays_handler:
            plays = plays_handler(plays)
        playbook_dir = os.path.join(self.run_dir, "playbook")
        playbook_dst = os.path.join(playbook_dir, "main.yml")
        os.makedirs(playbook_dir, mode=0o700, exist_ok=True)
        with open(playbook_dst, "w") as f:
            os.fchmod(f.fileno(), 0o600)
            yaml.safe_dump(plays, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return playbook_dst

    def _run_playbook(self, generate_playbook: callable, **kwargs):
        os.makedirs(self.run_dir, mode=0o700, exist_ok=True)
        os.chmod(self.run_dir, 0o700)
        try:
            inventory = self.generate_inventory()
            playbook = generate_playbook()
            runner = SuperPlaybookRunner(
                inventory=inventory,
                playbook=playbook,
                project_dir=self.run_dir,
                safety_mode="playbook_unsafe",
                inventory_safety="json_escape",
            )
            # Keep task progress visible; the credential import uses no_log.
            kwargs.setdefault("quiet", False)
            return runner.run(**kwargs)
        finally:
            self.delete_runtime_dir()

    def delete_runtime_dir(self):
        # The generated playbook contains a component key, including in debug
        # mode. Do not retain it or the inventory after success or failure.
        shutil.rmtree(self.run_dir, ignore_errors=True)

    def _run(self, cb_func: callable, **kwargs):
        try:
            self.deployment.date_start = timezone.now()
            cb = cb_func(**kwargs)
            self.deployment.status = cb.status
        except Exception as e:
            logger.error("Error: {}".format(e))
            self.deployment.status = "error"
        finally:
            self.deployment.date_finished = timezone.now()
            with safe_db_connection():
                self.deployment.save()
        self.delete_runtime_dir()
