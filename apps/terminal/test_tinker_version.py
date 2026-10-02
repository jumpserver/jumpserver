from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import yaml
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from jinja2 import Environment
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


@override_settings(SITE_URL='https://core.example.test')
class AppletHostDeployOptionsTests(TestCase):
    retired_options = {
        'RDS_Licensing': True,
        'RDS_LicenseServer': 'license.example.test',
        'RDS_LicensingMode': 4,
        'RDS_fSingleSessionPerUser': 0,
        'RDS_MaxDisconnectionTime': 120000,
        'RDS_RemoteAppLogoffTimeLimit': 60000,
    }

    def setUp(self):
        from assets.models import Platform
        from orgs.utils import tmp_to_builtin_org

        self.enterContext(tmp_to_builtin_org(system=1))
        self.platform, _ = Platform.objects.get_or_create(
            name='RemoteAppHost', defaults={'category': 'host', 'type': 'windows'},
        )
        self.options = {
            'CORE_HOST': 'https://saved-core.example.test', 'IGNORE_VERIFY_CERTS': False,
            'RDS_LICENSE_SERVER': 'current-license.example.test',
            **self.retired_options,
        }

    def test_new_host_ignores_retired_options_and_does_not_expose_them(self):
        serializer = AppletHostSerializer(data={
            'name': 'new-publish-host', 'address': '192.0.2.11', 'deploy_options': self.options.copy(),
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        host = serializer.save()
        host.refresh_from_db()
        expected = {key: value for key, value in self.options.items() if key not in self.retired_options}
        self.assertEqual(host.deploy_options, expected)
        self.assertEqual(serializer.data['deploy_options'], expected)
        for field in self.retired_options:
            self.assertNotIn(field, serializer.fields['deploy_options'].fields)

    def test_new_host_defaults_to_existing_windows_license_configuration(self):
        for options in ({}, {'RDS_LICENSE_SERVER': ''}, {'RDS_LICENSE_SERVER': '   '}):
            with self.subTest(options=options):
                serializer = AppletHostSerializer(data={
                    'name': f'publish-host-{uuid4()}', 'address': '192.0.2.14',
                    'deploy_options': {**self.retired_options, **options},
                })
                self.assertTrue(serializer.is_valid(), serializer.errors)
                host = serializer.save()
                host.refresh_from_db()
                self.assertEqual(host.deploy_options['RDS_LICENSE_SERVER'], '')
                self.assertEqual(serializer.data['deploy_options']['RDS_LICENSE_SERVER'], '')
                for field in self.retired_options:
                    self.assertNotIn(field, host.deploy_options)

    def test_update_preserves_historical_options_and_ignores_old_client_changes(self):
        legacy_options = self.options.copy()
        legacy_options.pop('RDS_LICENSE_SERVER')
        host = AppletHost.objects.create(
            name='existing-publish-host', address='192.0.2.12', platform=self.platform,
            deploy_options=legacy_options,
        )
        self.assertEqual(AppletHostSerializer(host).data['deploy_options']['RDS_LICENSE_SERVER'], '')
        self.assertNotIn('RDS_LICENSE_SERVER', host.deploy_options)
        for partial in (True, False):
            with self.subTest(partial=partial):
                serializer = AppletHostSerializer(host, data={
                    'name': host.name, 'address': host.address,
                    'deploy_options': {
                        **self.options, 'CORE_HOST': 'https://new-core.example.test',
                        'IGNORE_VERIFY_CERTS': True,
                        **dict.fromkeys(self.retired_options, 999),
                    },
                }, partial=partial)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                serializer.save()
                host.refresh_from_db()
                self.assertEqual(host.deploy_options, {
                    **self.options, 'CORE_HOST': 'https://new-core.example.test',
                    'IGNORE_VERIFY_CERTS': True,
                })
                for field in self.retired_options:
                    self.assertNotIn(field, serializer.data['deploy_options'])

    def test_updates_keep_omitted_connection_and_historical_options(self):
        host = AppletHost.objects.create(
            name='partial-publish-host', address='192.0.2.13', platform=self.platform,
            deploy_options=self.options.copy(),
        )
        expected = self.options.copy()
        for partial in (True, False):
            for options in (
                {'RDS_LICENSE_SERVER': 'new-license.example.test'},
                {'IGNORE_VERIFY_CERTS': False},
                {'CORE_HOST': 'https://new-core.example.test'},
                {'RDS_LICENSE_SERVER': ''},
            ):
                with self.subTest(partial=partial, options=options):
                    serializer = AppletHostSerializer(host, data={
                        'name': host.name, 'address': host.address, 'deploy_options': options,
                    }, partial=partial)
                    self.assertTrue(serializer.is_valid(), serializer.errors)
                    serializer.save()
                    host.refresh_from_db()
                    expected.update(options)
                    self.assertEqual(host.deploy_options, expected)

        serializer = AppletHostSerializer(host, data={'comment': 'Updated description'}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        host.refresh_from_db()
        self.assertEqual(host.deploy_options, expected)


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
        self.assertTrue(variables['IGNORE_VERIFY_CERTS'])

    def test_invalid_core_url_is_rejected_before_deployment(self):
        self.host.deploy_options = {'CORE_HOST': 'ftp://core.example.test'}
        with self.assertRaises(ValidationError):
            self.manager.generate_initial_playbook()

    def test_retired_options_never_reach_initial_or_applet_playbooks(self):
        retired = AppletHostDeployOptionsTests.retired_options
        options = {
            **retired, 'CORE_HOST': 'https://saved-core.example.test', 'IGNORE_VERIFY_CERTS': False,
        }
        self.host.deploy_options = options.copy()
        self.manager.applet = SimpleNamespace(name='weblite')
        generators = (
            self.manager.generate_initial_playbook,
            self.manager.generate_install_applet_playbook,
            self.manager.generate_install_all_playbook,
            self.manager.generate_uninstall_applet_playbook,
        )
        with TemporaryDirectory() as directory:
            self.manager.run_dir = directory
            for generate in generators:
                with self.subTest(playbook=generate.__name__):
                    text = Path(generate()).read_text()
                    for field in retired:
                        self.assertNotIn(field, text)
                    play = yaml.safe_load(text)[0]
                    if generate == self.manager.generate_initial_playbook:
                        self.assertEqual(play['vars']['CORE_HOST'], options['CORE_HOST'])
                        self.assertFalse(play['vars']['IGNORE_VERIFY_CERTS'])
                        install = next(block for block in play['tasks'] if block['tags'] == ['install'])
                        features = [task['ansible.windows.win_feature'] for task in install['block']
                                    if 'ansible.windows.win_feature' in task]
                        self.assertIn({'name': 'RDS-RD-Server', 'state': 'present',
                                       'include_management_tools': True}, features)
                    elif generate == self.manager.generate_install_applet_playbook:
                        self.assertEqual(play['vars']['applet_name'], 'weblite')
        self.assertEqual(self.host.deploy_options, options)

    def test_license_server_write_requires_the_new_explicit_option(self):
        env = Environment()
        cases = (
            ({}, ''),
            ({'RDS_LICENSE_SERVER': ''}, ''),
            ({'RDS_LICENSE_SERVER': '  '}, ''),
            ({'RDS_LICENSE_SERVER': ' license.example.test '}, 'license.example.test'),
            ({'RDS_LICENSE_SERVER': '127.0.0.1'}, '127.0.0.1'),
        )
        with TemporaryDirectory() as directory:
            self.manager.run_dir = directory
            for legacy_enabled in (None, False, True):
                legacy = {**AppletHostDeployOptionsTests.retired_options, 'RDS_LicenseServer': '127.0.0.1'}
                if legacy_enabled is None:
                    legacy.pop('RDS_Licensing')
                else:
                    legacy['RDS_Licensing'] = legacy_enabled
                for options, server in cases:
                    with self.subTest(legacy_enabled=legacy_enabled, options=options):
                        self.host.deploy_options = {**legacy, **options}
                        play = yaml.safe_load(Path(self.manager.generate_initial_playbook()).read_text())[0]
                        install = next(block for block in play['tasks'] if block['tags'] == ['install'])
                        writes = [task for task in install['block'] if 'ansible.windows.win_regedit' in task]
                        self.assertEqual(len(writes), 1)
                        task = writes[0]
                        self.assertEqual(task['ansible.windows.win_regedit']['name'], 'LicenseServers')
                        self.assertEqual(bool(env.compile_expression(task['when'])(**play['vars'])), bool(server))
                        configured = env.from_string(task['ansible.windows.win_regedit']['data']).render(play['vars'])
                        self.assertEqual(configured, server)
                        self.assertEqual(self.host.deploy_options, {**legacy, **options})

    def test_deployment_passes_core_connection_options_to_tinker(self):
        env = Environment()
        credentials = {'name': '[Tinker]-publish-host', 'access_key': 'id:test-secret'}
        with TemporaryDirectory() as directory:
            self.manager.run_dir = directory
            for url, skip in [('http://core.example.test', True), ('https://core.example.test', True),
                              ('https://core.example.test', False)]:
                with self.subTest(url=url, skip=skip):
                    self.host.deploy_options = {'CORE_HOST': url, 'IGNORE_VERIFY_CERTS': skip}
                    path = self.manager.generate_initial_playbook(credentials)
                    play = yaml.safe_load(Path(path).read_text())[0]
                    deploy = next(block for block in play['tasks'] if block['tags'] == ['deploy'])
                    parameters = deploy['block'][0]['ansible.windows.win_powershell']['parameters']
                    config = {name: env.from_string(value).render(play['vars'])
                              for name, value in parameters.items()}
                    self.assertEqual(config['CORE_HOST'], url)
                    self.assertEqual(config['IGNORE_VERIFY_CERTS'], str(skip).lower())
                    self.assertEqual(config['HOST_ID'], str(self.host.id))
                    self.assertEqual(config['ComponentKey'], credentials['access_key'])

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
