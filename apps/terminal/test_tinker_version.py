from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from terminal import const
from terminal.api.applet.host import AppletHostFilterSet
from terminal.automations.deploy_applet_host import DeployAppletHostManager
from terminal.models import AppletHost, Terminal
from terminal.serializers.applet_host import AppletHostSerializer
from terminal.utils.tinker import get_tinker_version_status, get_tinker_upgrade_message


class TinkerVersionTests(SimpleTestCase):
    def test_missing_and_old_versions_require_upgrade(self):
        for version in ['', None, 'v0.3.0', 'v0.2.99', 'v0.3.1-dev']:
            with self.subTest(version=version):
                self.assertIn(get_tinker_version_status(version), ('unknown', 'unsupported'))
                self.assertIn('redeploy', get_tinker_upgrade_message(version))
                self.assertIn(const.TINKER_MIN_VERSION, get_tinker_upgrade_message(version))
        for version in ['v0.3.1', '0.3.1', 'v0.3.10']:
            with self.subTest(version=version):
                self.assertEqual(get_tinker_upgrade_message(version), '')

    def test_startup_only_updates_version_for_bound_tinker(self):
        terminal = Terminal(id=uuid4(), type='tinker')
        host = AppletHost(terminal=terminal)
        host.save = Mock()
        request = SimpleNamespace(user=SimpleNamespace(terminal=terminal))
        host.check_terminal_binding(request, tinker_version='v0.3.1')
        self.assertEqual(host.tinker_version, 'v0.3.1')
        host.save.assert_called_once_with(update_fields=['date_synced', 'tinker_version'])
        request.user.terminal = Terminal(id=uuid4(), type='tinker')
        with self.assertRaises(PermissionDenied):
            host.check_terminal_binding(request, tinker_version='v99.0.0')
        self.assertEqual(host.tinker_version, 'v0.3.1')
        request.user.terminal = Terminal(id=terminal.id, type='razor')
        with self.assertRaises(ValidationError):
            host.check_terminal_binding(request, tinker_version='v99.0.0')

    def test_host_api_exposes_versions_and_upgrade_instruction(self):
        host = AppletHost(tinker_version='v0.3.0')
        serializer = AppletHostSerializer()
        self.assertEqual(serializer.get_tinker_min_version(host), const.TINKER_MIN_VERSION)
        self.assertEqual(serializer.get_tinker_target_version(host), const.TINKER_TARGET_VERSION)
        self.assertEqual(serializer.get_tinker_version_status(host), 'unsupported')
        self.assertIn('redeploy', serializer.get_tinker_upgrade_message(host))
        for field in ['auto_create_accounts', 'accounts_create_amount', 'using_same_account']:
            self.assertNotIn(field, serializer.fields)

    def test_needs_attention_filter_includes_missing_reports_and_old_versions(self):
        queryset = Mock()
        candidates = queryset.filter.return_value
        versions = candidates.order_by.return_value.values_list.return_value.distinct.return_value
        versions.iterator.return_value = iter(['', 'v0.3.0', 'v0.3.1', 'v0.3.10'])
        AppletHostFilterSet.filter_needs_attention(queryset, 'needs_attention', True)
        candidates.filter.assert_called_once_with(tinker_version__in=['', 'v0.3.0', 'v0.3.10'])


@override_settings(SITE_URL='https://core.example.test', APPLET_DOWNLOAD_HOST='https://downloads.example.test')
class TinkerDeploymentTests(SimpleTestCase):
    def setUp(self):
        self.host = Mock(
            id=uuid4(), deploy_options={}, tinker_version=const.TINKER_TARGET_VERSION,
            date_synced=timezone.now(), terminal=Mock(),
        )
        self.host.name = 'publish-host'
        self.manager = object.__new__(DeployAppletHostManager)
        self.manager.deployment = Mock(id=uuid4(), host=self.host)
        self.manager.install_applets = True

    def test_installer_uses_target_version_and_no_host_auth_switch(self):
        self.host.deploy_options = {'TINKER_VERSION': 'v0.1.0', 'RDP_TOKEN_LOGIN': False}
        self.manager._generate_playbook = lambda name, handler: handler([{'vars': {}}])
        variables = self.manager.generate_initial_playbook()[0]['vars']
        self.assertEqual(variables['TINKER_VERSION'], const.TINKER_TARGET_VERSION)
        self.assertNotIn('RDP_TOKEN_LOGIN', variables)
        self.assertNotIn('BOOTSTRAP_TOKEN', variables)
        self.assertNotIn('TINKER_ACCESS_KEY', variables)
        self.assertFalse(variables['IGNORE_VERIFY_CERTS'])

    def test_invalid_core_url_is_rejected_before_deployment(self):
        self.host.deploy_options = {'CORE_HOST': 'http://core.example.test'}
        with self.assertRaises(ValidationError):
            self.manager.generate_initial_playbook()

    def test_download_or_install_failure_keeps_component_identity_and_version(self):
        old_terminal = self.host.terminal
        old_report = self.host.date_synced
        success, failed = SimpleNamespace(status='success'), SimpleNamespace(status='failed')
        for results, phases in [([failed], ['prepare']), ([success, failed], ['prepare', 'install'])]:
            with self.subTest(phases=phases), patch.object(self.manager, 'create_tinker_credentials') as create:
                self.manager._run_playbook = Mock(side_effect=results)
                self.assertIs(self.manager._run_initial_deploy(), failed)
                self.assertEqual([call.kwargs['tags'] for call in self.manager._run_playbook.call_args_list], phases)
                create.assert_not_called()
                self.assertIs(self.host.terminal, old_terminal)
                self.assertEqual(self.host.tinker_version, const.TINKER_TARGET_VERSION)
                self.assertEqual(self.host.date_synced, old_report)
                old_terminal.delete.assert_not_called()
                self.host.save.assert_not_called()

    def test_install_exception_keeps_component_identity(self):
        old_terminal = self.host.terminal
        self.manager._run_playbook = Mock(side_effect=[SimpleNamespace(status='success'), RuntimeError('installer failed')])
        with patch.object(self.manager, 'create_tinker_credentials') as create, \
                self.assertRaisesMessage(RuntimeError, 'installer failed'):
            self.manager._run_initial_deploy()
        self.assertIs(self.host.terminal, old_terminal)
        old_terminal.delete.assert_not_called()
        create.assert_not_called()

    @override_settings(SECURITY_SERVICE_ACCOUNT_REGISTRATION=False, BOOTSTRAP_TOKEN='')
    def test_credentials_are_passed_only_after_windows_installation(self):
        credentials = {'name': '[Tinker]-publish-host', 'access_key': 'id:test-secret'}
        phases = []
        self.manager._generate_playbook = lambda name, handler: handler([{'vars': {}}])

        def run_playbook(generate, *, tags):
            phases.append(tags)
            variables = generate()[0]['vars']
            self.assertNotIn('BOOTSTRAP_TOKEN', variables)
            if tags != 'deploy':
                create.assert_not_called()
                self.assertNotIn('TINKER_ACCESS_KEY', variables)
            else:
                create.assert_called_once_with()
                self.assertEqual(variables['HOST_NAME'], credentials['name'])
                self.assertEqual(variables['TINKER_ACCESS_KEY'], credentials['access_key'])
            return SimpleNamespace(status='success')

        self.manager._run_playbook = run_playbook
        with patch.object(self.manager, 'create_tinker_credentials', return_value=credentials) as create:
            self.assertEqual(self.manager._run_initial_deploy().status, 'success')
        self.assertEqual(phases, ['prepare', 'install', 'deploy'])

    def test_deployment_requires_a_fresh_target_version_report(self):
        success = SimpleNamespace(status='success')
        self.manager._run_playbook = Mock(return_value=success)
        with patch.object(self.manager, 'create_tinker_credentials', return_value={}):
            for version, report_time in [('', None), ('v0.3.0', timezone.now()), ('v0.3.1', None)]:
                self.host.tinker_version, self.host.date_synced = version, report_time
                with self.subTest(version=version, report_time=report_time), \
                        self.assertRaisesMessage(RuntimeError, 'redeploy'):
                    self.manager._run_initial_deploy()
            self.host.tinker_version = const.TINKER_TARGET_VERSION
            self.host.date_synced = timezone.now()
            self.assertIs(self.manager._run_initial_deploy(), success)
        self.host.refresh_from_db.assert_called_with(fields=['tinker_version', 'date_synced'])

    @override_settings(DEBUG_DEV=True)
    def test_private_credential_playbook_is_removed_even_after_runner_failure(self):
        credentials = {'name': '[Tinker]-publish-host', 'access_key': 'id:test-secret'}
        with TemporaryDirectory() as directory:
            self.manager.run_dir = str(Path(directory) / 'deployment')
            self.manager.generate_inventory = Mock(return_value='inventory.yml')

            def run(**kwargs):
                run_dir = Path(self.manager.run_dir)
                playbook = run_dir / 'playbook/main.yml'
                self.assertEqual(run_dir.stat().st_mode & 0o777, 0o700)
                self.assertEqual(playbook.stat().st_mode & 0o777, 0o600)
                self.assertIn(credentials['access_key'], playbook.read_text())
                self.assertNotIn('BOOTSTRAP_TOKEN', playbook.read_text())
                raise RuntimeError('runner failed')

            with patch('terminal.automations.deploy_applet_host.SuperPlaybookRunner') as runner:
                runner.return_value.run.side_effect = run
                with self.assertRaisesMessage(RuntimeError, 'runner failed'):
                    self.manager._run_playbook(lambda: self.manager.generate_initial_playbook(credentials), tags='deploy')
            self.assertFalse(Path(self.manager.run_dir).exists())


@override_settings(SECURITY_SERVICE_ACCOUNT_REGISTRATION=False, BOOTSTRAP_TOKEN='')
class TinkerCredentialCreationTests(TestCase):
    def setUp(self):
        from assets.models import Platform
        from terminal.models import CommandStorage, ReplayStorage
        from terminal.serializers import TerminalRegistrationSerializer

        CommandStorage.objects.get_or_create(name='default', defaults={'type': 'server'})
        ReplayStorage.objects.get_or_create(name='default', defaults={'type': 'server'})
        platform = Platform.objects.create(name='tinker-deployment-test', category='host', type='windows')
        self.host = AppletHost.objects.create(name='publish-host', address='192.0.2.10', platform=platform)
        old = TerminalRegistrationSerializer(data={'name': '[Tinker]-old', 'type': 'tinker'})
        old.is_valid(raise_exception=True)
        self.old_terminal = old.save()
        self.old_key = self.old_terminal.user.access_key
        self.host.terminal = self.old_terminal
        self.host.tinker_version = const.TINKER_TARGET_VERSION
        self.host.date_synced = timezone.now()
        self.host.save()
        self.manager = DeployAppletHostManager(Mock(host=self.host))

    def test_core_creates_bound_key_with_public_registration_disabled(self):
        from authentication.models import AccessKey
        from common.permissions import WithBootstrapToken
        from rbac.builtin import BuiltinRole

        self.assertFalse(WithBootstrapToken().check_can_register())
        credentials = self.manager.create_tinker_credentials()
        self.host.refresh_from_db()
        terminal = self.host.terminal
        self.assertEqual(terminal.type, 'tinker')
        self.assertTrue(terminal.user.is_service_account)
        self.assertTrue(terminal.user.system_roles.filter(id=BuiltinRole.system_component.id).exists())
        self.assertEqual(credentials, {'name': terminal.name, 'access_key': terminal.user.access_key.get_full_value()})
        self.assertEqual(self.host.tinker_version, '')
        self.assertIsNone(self.host.date_synced)
        self.assertFalse(AccessKey.objects.filter(pk=self.old_key.pk).exists())
        self.host.check_terminal_binding(Mock(user=terminal.user), tinker_version=const.TINKER_TARGET_VERSION)
        self.assertFalse(WithBootstrapToken().check_can_register())

    def test_binding_failure_rolls_back_new_key_and_preserves_old_identity(self):
        from authentication.models import AccessKey
        from users.models import User

        before = (Terminal.objects.count(), User.objects.count(), AccessKey.objects.count())
        # Fail after creating the new terminal/user/key and saving its host binding.
        with patch.object(Terminal, 'delete', side_effect=RuntimeError('retire failed')), \
                self.assertRaisesMessage(RuntimeError, 'retire failed'):
            self.manager.create_tinker_credentials()
        self.host.refresh_from_db()
        self.assertEqual(self.host.terminal_id, self.old_terminal.pk)
        self.assertEqual(self.host.tinker_version, const.TINKER_TARGET_VERSION)
        self.assertIsNotNone(self.host.date_synced)
        self.assertTrue(AccessKey.objects.filter(pk=self.old_key.pk, is_active=True).exists())
        self.assertEqual((Terminal.objects.count(), User.objects.count(), AccessKey.objects.count()), before)
