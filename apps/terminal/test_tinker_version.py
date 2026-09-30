from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import SimpleTestCase, override_settings
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
        self.assertFalse(variables['IGNORE_VERIFY_CERTS'])

    def test_invalid_core_url_is_rejected_before_deployment(self):
        self.host.deploy_options = {'CORE_HOST': 'http://core.example.test'}
        with self.assertRaises(ValidationError):
            self.manager.generate_initial_playbook()

    def test_prepare_failure_keeps_running_component_and_version(self):
        failed = SimpleNamespace(status='failed')
        self.manager._run_playbook = Mock(return_value=failed)
        with patch.object(self.manager, 'detach_terminal') as detach:
            self.assertIs(self.manager._run_initial_deploy(), failed)
        detach.assert_not_called()
        self.assertEqual(self.host.tinker_version, const.TINKER_TARGET_VERSION)

    def test_deployment_clears_stale_report_and_checks_new_report(self):
        old_terminal = self.host.terminal
        self.manager.detach_terminal()
        self.assertEqual(self.host.tinker_version, '')
        self.assertIsNone(self.host.date_synced)
        self.host.save.assert_called_once_with(update_fields=['terminal', 'tinker_version', 'date_synced'])
        old_terminal.delete.assert_called_once()

        success = SimpleNamespace(status='success')
        self.manager._run_playbook = Mock(return_value=success)
        for version, report_time in [('', None), ('v0.3.0', timezone.now()), ('v0.3.1', None)]:
            self.host.tinker_version, self.host.date_synced = version, report_time
            with self.subTest(version=version, report_time=report_time), \
                    patch.object(self.manager, 'detach_terminal'), \
                    patch('terminal.automations.deploy_applet_host.cache'), \
                    self.assertRaisesMessage(RuntimeError, 'redeploy'):
                self.manager._run_initial_deploy()
        self.host.tinker_version = const.TINKER_TARGET_VERSION
        self.host.date_synced = timezone.now()
        with patch.object(self.manager, 'detach_terminal'), patch('terminal.automations.deploy_applet_host.cache'):
            self.assertIs(self.manager._run_initial_deploy(), success)
        self.host.refresh_from_db.assert_called_with(fields=['tinker_version', 'date_synced'])
