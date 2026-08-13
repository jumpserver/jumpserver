import os
import tempfile
from unittest import mock

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError
from django.test.utils import override_settings
import yaml

from assets.utils.platform_package import locate_package_root
from terminal.models import Applet, AppProvider, Terminal, VirtualApp
from terminal.const import ComponentLoad
from terminal.automations.deploy_app_provider import DeployAppProviderManager
from terminal.serializers import AppProviderSerializer


class PackageRootLocateTests(SimpleTestCase):
    def make_file(self, base_dir, relative_path):
        path = os.path.join(base_dir, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf8') as f:
            f.write('test')
        return path

    def test_locate_package_root_supports_files_extracted_to_current_dir(self):
        with tempfile.TemporaryDirectory() as extract_to:
            self.make_file(extract_to, 'manifest.yml')
            self.make_file(extract_to, 'icon.png')

            root = locate_package_root(extract_to, 'demo.zip', 'manifest.yml')

            self.assertEqual(root, extract_to)

    def test_locate_package_root_supports_single_wrapped_directory(self):
        with tempfile.TemporaryDirectory() as extract_to:
            wrapped_dir = os.path.join(extract_to, 'demo')
            self.make_file(wrapped_dir, 'manifest.yml')
            self.make_file(wrapped_dir, 'icon.png')

            root = locate_package_root(extract_to, 'demo.zip', 'manifest.yml')

            self.assertEqual(root, wrapped_dir)

    def test_applet_locate_pkg_root_supports_files_extracted_to_current_dir(self):
        with tempfile.TemporaryDirectory() as extract_to:
            self.make_file(extract_to, 'manifest.yml')

            root = Applet.locate_pkg_root(extract_to, 'demo.zip')

            self.assertEqual(root, extract_to)

    def test_virtualapp_locate_pkg_root_supports_files_extracted_to_current_dir(self):
        with tempfile.TemporaryDirectory() as extract_to:
            self.make_file(extract_to, 'manifest.yml')

            root = VirtualApp.locate_pkg_root(extract_to, 'demo.zip')

            self.assertEqual(root, extract_to)


class VirtualAppProviderSelectionTests(SimpleTestCase):
    def setUp(self):
        self.app = VirtualApp(id='00000000-0000-0000-0000-000000000001', name='demo')
        self.user = mock.Mock(id='00000000-0000-0000-0000-000000000002')

    @mock.patch('terminal.models.virtualapp.virtualapp.cache')
    def test_select_provider_prefers_previous_available_provider(self, mocked_cache):
        provider1 = mock.Mock(
            id='00000000-0000-0000-0000-000000000003',
            load=ComponentLoad.normal,
            container_count=0,
        )
        provider2 = mock.Mock(
            id='00000000-0000-0000-0000-000000000004',
            load=ComponentLoad.normal,
            container_count=1,
        )
        mocked_cache.get.return_value = str(provider2.id)
        self.app.filter_available_providers = mock.Mock(return_value=[provider1, provider2])

        selected = self.app.select_provider(self.user)

        self.assertIs(selected, provider2)

    @mock.patch('terminal.models.virtualapp.virtualapp.cache')
    def test_select_provider_does_not_prefer_degraded_provider(self, mocked_cache):
        normal = mock.Mock(
            id='00000000-0000-0000-0000-000000000003',
            load=ComponentLoad.normal,
            container_count=1,
        )
        preferred_high = mock.Mock(
            id='00000000-0000-0000-0000-000000000004',
            load=ComponentLoad.high,
            container_count=0,
        )
        mocked_cache.get.return_value = str(preferred_high.id)
        self.app.filter_available_providers = mock.Mock(
            return_value=[preferred_high, normal]
        )

        selected = self.app.select_provider(self.user)

        self.assertIs(selected, normal)

    @mock.patch('terminal.models.virtualapp.virtualapp.cache')
    def test_select_provider_uses_lower_load_then_container_count(self, mocked_cache):
        high = mock.Mock(
            id='00000000-0000-0000-0000-000000000003',
            load=ComponentLoad.high,
            container_count=0,
        )
        normal_busy = mock.Mock(
            id='00000000-0000-0000-0000-000000000004',
            load=ComponentLoad.normal,
            container_count=2,
        )
        normal_idle = mock.Mock(
            id='00000000-0000-0000-0000-000000000005',
            load=ComponentLoad.normal,
            container_count=0,
        )
        mocked_cache.get.return_value = None
        self.app.filter_available_providers = mock.Mock(
            return_value=[high, normal_busy, normal_idle]
        )

        selected = self.app.select_provider(self.user)

        self.assertIs(selected, normal_idle)

    def test_filter_available_providers_requires_success_and_online(self):
        online = mock.Mock(load=ComponentLoad.normal, connection_ready=True)
        offline = mock.Mock(load=ComponentLoad.offline, connection_ready=True)
        publications = mock.Mock()
        publications.select_related.return_value = [
            mock.Mock(provider=online),
            mock.Mock(provider=offline),
        ]
        publication_manager = mock.Mock()
        publication_manager.filter.return_value = publications
        with mock.patch.object(
            VirtualApp, 'publications', new=mock.PropertyMock(return_value=publication_manager)
        ):
            providers = self.app.filter_available_providers()

        self.assertEqual(providers, [online])

    def test_filter_available_providers_excludes_unready_ssh_provider(self):
        ready = mock.Mock(load=ComponentLoad.normal, connection_ready=True)
        unready = mock.Mock(load=ComponentLoad.normal, connection_ready=False)
        publications = mock.Mock()
        publications.select_related.return_value = [
            mock.Mock(provider=ready), mock.Mock(provider=unready),
        ]
        publication_manager = mock.Mock()
        publication_manager.filter.return_value = publications
        with mock.patch.object(
            VirtualApp, 'publications', new=mock.PropertyMock(return_value=publication_manager)
        ):
            providers = self.app.filter_available_providers()

        self.assertEqual(providers, [ready])


class AppProviderRuntimeTests(SimpleTestCase):
    def test_provider_serializer_exposes_provider_comment(self):
        provider = AppProvider(name='provider-one', hostname='192.0.2.10', comment='Provider note')

        data = AppProviderSerializer(instance=provider).data

        self.assertEqual(data['comment'], 'Provider note')

    def test_provider_update_binds_existing_host_to_nested_serializer(self):
        host = mock.Mock()
        provider = mock.Mock(host=host)

        serializer = AppProviderSerializer(instance=provider)

        self.assertIs(serializer.fields['host'].instance, host)

    @mock.patch('terminal.serializers.virtualapp_provider.Platform.objects.get')
    @mock.patch('assets.serializers.HostSerializer.to_internal_value')
    def test_provider_host_update_ignores_represented_asset_id(
        self, mocked_to_internal_value, mocked_platform_get
    ):
        from terminal.serializers.virtualapp_provider import AppProviderHostSerializer

        mocked_platform_get.return_value.id = 'virtual-app-platform'
        mocked_to_internal_value.side_effect = lambda data: data
        serializer = AppProviderHostSerializer()
        result = serializer.to_internal_value({
            'id': 'existing-host-id',
            'name': 'provider-one',
            'address': '192.0.2.10',
            'protocols': [{'name': 'ssh', 'port': 22}],
        })

        self.assertNotIn('id', result)
        self.assertEqual(result['platform'], 'virtual-app-platform')

    def test_managed_provider_is_forced_to_ssh_and_docker(self):
        serializer = AppProviderSerializer()
        attrs = {
            'host': {'name': 'provider-one', 'address': '192.0.2.10'},
        }

        with mock.patch.object(AppProvider.objects, 'filter') as mocked_filter:
            mocked_filter.return_value.exists.return_value = False
            result = serializer.validate(attrs)

        self.assertEqual(result['name'], 'provider-one')
        self.assertEqual(result['hostname'], '192.0.2.10')
        self.assertEqual(result['runtime_type'], AppProvider.RuntimeType.docker)
        self.assertEqual(result['connection_mode'], AppProvider.ConnectionMode.ssh)

    def test_address_falls_back_to_legacy_hostname(self):
        provider = AppProvider(hostname='192.0.2.10')

        self.assertEqual(provider.address, '192.0.2.10')

    def test_address_uses_bound_host(self):
        provider = AppProvider(hostname='legacy-address')
        provider.__dict__['host_id'] = '00000000-0000-0000-0000-000000000001'
        host = mock.Mock(address='198.51.100.10')
        with mock.patch.object(
            AppProvider, 'host', new=mock.PropertyMock(return_value=host)
        ):
            self.assertEqual(provider.address, '198.51.100.10')

    @mock.patch('terminal.models.virtualapp.provider.cache')
    def test_container_count_uses_reported_provider_status(self, mocked_cache):
        provider = AppProvider(id='00000000-0000-0000-0000-000000000001')
        mocked_cache.get.return_value = [{'id': 'one'}, {'id': 'two'}]

        self.assertEqual(provider.container_count, 2)

    def test_ssh_provider_requires_host_ssh_protocol_and_account(self):
        provider = AppProvider(connection_mode=AppProvider.ConnectionMode.ssh)
        provider.__dict__['host_id'] = '00000000-0000-0000-0000-000000000001'
        host = mock.Mock()
        host.protocols.filter.return_value.exists.return_value = True
        host.accounts.active.return_value.order_by.return_value.first.return_value = mock.Mock()
        with mock.patch.object(
            AppProvider, 'host', new=mock.PropertyMock(return_value=host)
        ):
            self.assertTrue(provider.connection_ready)

        host.accounts.active.return_value.order_by.return_value.first.return_value = None
        with mock.patch.object(
            AppProvider, 'host', new=mock.PropertyMock(return_value=host)
        ):
            self.assertFalse(provider.connection_ready)


class AppProviderTerminalBindingTests(TestCase):
    def setUp(self):
        self.terminal = Terminal.objects.create(name='panda', type='panda')

    def test_managed_provider_replaces_legacy_direct_provider(self):
        legacy = AppProvider.objects.create(
            name='legacy-direct', hostname='192.0.2.10',
            connection_mode=AppProvider.ConnectionMode.direct,
            terminal=self.terminal,
        )
        managed = AppProvider.objects.create(
            name='managed-ssh', hostname='192.0.2.10',
            connection_mode=AppProvider.ConnectionMode.ssh,
        )

        managed.bind_terminal(self.terminal)

        self.assertFalse(AppProvider.objects.filter(pk=legacy.pk).exists())
        managed.refresh_from_db()
        self.assertEqual(managed.terminal_id, self.terminal.id)

    def test_provider_does_not_take_terminal_from_another_managed_provider(self):
        AppProvider.objects.create(
            name='existing-ssh', hostname='192.0.2.10',
            connection_mode=AppProvider.ConnectionMode.ssh,
            terminal=self.terminal,
        )
        managed = AppProvider.objects.create(
            name='managed-ssh', hostname='198.51.100.10',
            connection_mode=AppProvider.ConnectionMode.ssh,
        )

        with self.assertRaises(ValidationError):
            managed.bind_terminal(self.terminal)


class AppProviderDeploymentTests(SimpleTestCase):
    @mock.patch(
        'terminal.automations.deploy_app_provider.SuperPlaybookRunner'
    )
    def test_deployment_keeps_normal_playbook_output_visible(self, mocked_runner):
        provider = mock.Mock(host=mock.Mock())
        deployment = mock.Mock(provider=provider, publication_id=None)
        result = mock.Mock(status='success')
        mocked_runner.return_value.run.return_value = result

        with mock.patch.object(
            DeployAppProviderManager, 'generate_inventory', return_value='/tmp/inventory'
        ), mock.patch.object(
            DeployAppProviderManager, 'generate_playbook', return_value='/tmp/playbook'
        ):
            DeployAppProviderManager(deployment).run()

        mocked_runner.return_value.run.assert_called_once_with(quiet=False)

    @override_settings(
        SITE_URL='https://core.example.com', BOOTSTRAP_TOKEN='bootstrap-test',
        DEBUG_DEV=True,
    )
    def test_generated_playbook_binds_panda_to_provider(self):
        provider = mock.Mock(
            id='00000000-0000-0000-0000-000000000010',
            host=mock.Mock(address='192.0.2.10'),
            deploy_options={
                'PANDA_IMAGE': 'jumpserver/panda:test',
                'PANDA_RANGE_PORTS': '7000-7100',
            },
        )
        provider.name = 'provider-one'
        deployment = mock.Mock(provider=provider, publication_id=None)
        with tempfile.TemporaryDirectory() as ansible_dir, override_settings(
            ANSIBLE_DIR=ansible_dir
        ):
            manager = DeployAppProviderManager(deployment)
            path = manager.generate_playbook()
            with open(path) as stream:
                play = yaml.safe_load(stream)[0]

        variables = play['vars']
        self.assertEqual(variables['PROVIDER_ID'], str(provider.id))
        self.assertEqual(variables['PANDA_HOST_IP'], '192.0.2.10')
        self.assertEqual(variables['PANDA_IMAGE'], 'jumpserver/panda:test')
        docker_service_task = next(
            task for task in play['tasks']
            if task['name'] == 'Ensure Docker service is running'
        )
        self.assertIn('ansible.builtin.systemd_service', docker_service_task)
        self.assertNotIn('ansible.builtin.service', docker_service_task)

    @override_settings(SITE_URL='https://core.example.com', BOOTSTRAP_TOKEN='token')
    def test_publish_playbook_pulls_virtual_app_image(self):
        provider = mock.Mock(
            id='00000000-0000-0000-0000-000000000010',
            host=mock.Mock(address='192.0.2.10'),
            deploy_options={},
        )
        provider.name = 'provider-one'
        publication = mock.Mock(app=mock.Mock(image_name='example/app:v1'))
        deployment = mock.Mock(
            provider=provider, publication_id='publication-id', publication=publication,
        )
        with tempfile.TemporaryDirectory() as ansible_dir, override_settings(
            ANSIBLE_DIR=ansible_dir
        ):
            path = DeployAppProviderManager(deployment).generate_playbook()
            with open(path) as stream:
                play = yaml.safe_load(stream)[0]

        self.assertEqual(play['vars']['APP_IMAGE'], 'example/app:v1')
        self.assertEqual(len(play['tasks']), 1)
