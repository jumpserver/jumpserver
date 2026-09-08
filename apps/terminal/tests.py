import os
import tempfile
from unittest.mock import Mock, patch

from unittest import mock

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError
from django.test.utils import override_settings
import yaml

from assets.utils.platform_package import locate_package_root
from terminal.models import Applet, AppProvider, Terminal, VirtualApp, VirtualAppPublication
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


class WebAppletDefaultsTests(SimpleTestCase):
    def test_builtin_install_skips_chrome_and_includes_web_applet(self):
        from unittest.mock import patch
        from terminal.applets import install_or_update_builtin_applets

        with patch.object(Applet, 'install_from_dir', return_value=None) as install:
            install_or_update_builtin_applets()
        names = [os.path.basename(call.args[0]) for call in install.call_args_list]
        self.assertIn('weblite', names)
        self.assertNotIn('chrome', names)

    def test_direct_mode_is_default_and_recording_endpoint_is_optional(self):
        from terminal.serializers.applet_host import DeployOptionsSerializer

        serializer = DeployOptionsSerializer(data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertFalse(serializer.validated_data['WEB_APPLET_RECORDING_ENABLED'])
        self.assertEqual(serializer.validated_data['WEB_PROXY_URL'], '')
        enabled = DeployOptionsSerializer(data={'WEB_APPLET_RECORDING_ENABLED': True})
        self.assertFalse(enabled.is_valid())
        self.assertIn('WEB_PROXY_URL', enabled.errors)


class DeployAppletHostManagerTests(SimpleTestCase):
    @patch('terminal.automations.deploy_applet_host.JMSInventory')
    def test_generate_inventory_excludes_localhost(self, inventory_class):
        from terminal.automations.deploy_applet_host import DeployAppletHostManager

        deployment = Mock()
        deployment.host = Mock()
        manager = DeployAppletHostManager(deployment)

        manager.generate_inventory()

        inventory_class.assert_called_once_with(
            [deployment.host],
            account_policy='privileged_only',
            exclude_localhost=True,
        )


class WebsiteConnectMethodTests(SimpleTestCase):
    def test_builtin_web_proxy_does_not_require_an_applet_host(self):
        from terminal.connect_methods import ConnectMethodUtil

        ConnectMethodUtil.refresh_methods()
        with (
            patch('terminal.connect_methods.AppletMethod.get_methods', return_value={}),
            patch('terminal.connect_methods.VirtualAppMethod.get_methods', return_value={}),
            patch('terminal.connect_methods.NativeClient.get_methods', return_value={}),
        ):
            methods = ConnectMethodUtil.get_protocols_connect_methods()
            web_proxy = ConnectMethodUtil.get_connect_method('web_proxy', 'http')
        ConnectMethodUtil.refresh_methods()

        self.assertEqual(methods['http'], [{
            'component': 'koko',
            'type': 'web',
            'endpoint_protocol': 'http',
            'value': 'web_proxy',
            'label': 'Built-in Browser',
        }])
        self.assertEqual(web_proxy, methods['http'][0])

class VirtualAppProviderSelectionTests(SimpleTestCase):
    def setUp(self):
        self.app = VirtualApp(id='00000000-0000-0000-0000-000000000001', name='demo')
        self.user = mock.Mock(id='00000000-0000-0000-0000-000000000002')

    @mock.patch('authentication.models.connection_token.VirtualApp.objects.filter')
    def test_connection_requires_provider_even_without_publications(self, apps):
        from authentication.models import ConnectionToken
        from common.exceptions import JMSException

        token = mock.Mock(
            connect_method_object={'type': 'virtual_app', 'value': self.app.name},
            user=self.user,
        )
        apps.return_value.first.return_value = self.app
        with mock.patch.object(self.app, 'select_provider', return_value=None):
            with self.assertRaisesMessage(JMSException, 'No provider available'):
                ConnectionToken.get_virtual_app_option(token)

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
    def test_provider_list_serializer_accepts_queryset(self):
        serializer = AppProviderSerializer(AppProvider.objects.none(), many=True)
        self.assertEqual(serializer.data, [])

    def test_provider_serializer_exposes_provider_comment(self):
        provider = AppProvider(name='provider-one', hostname='192.0.2.10', comment='Provider note')

        data = AppProviderSerializer(instance=provider).data

        self.assertEqual(data['comment'], 'Provider note')

    def test_provider_update_binds_existing_host_to_nested_serializer(self):
        host = mock.Mock()
        provider = mock.Mock(spec=AppProvider, host=host)

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

    def test_managed_provider_uses_docker_and_local_panda_service(self):
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
        self.assertEqual(result['service_url'], 'http://127.0.0.1:9001')

    @mock.patch('terminal.serializers.virtualapp_provider.Platform.objects.get')
    @mock.patch('assets.serializers.HostSerializer.to_internal_value', side_effect=lambda data: data)
    def test_partial_host_update_preserves_name_address_and_ssh_port(self, _internal, platform_get):
        platform_get.return_value.id = 'virtual-app-platform'
        host = mock.Mock(address='192.0.2.10')
        host.name = 'provider-one'
        provider = mock.Mock(spec=AppProvider, host=host)
        serializer = AppProviderSerializer(instance=provider, partial=True)

        host_data = serializer.fields['host'].to_internal_value({'comment': 'Updated'})
        with mock.patch.object(AppProvider.objects, 'filter') as providers:
            providers.return_value.exclude.return_value.exists.return_value = False
            result = serializer.validate({'host': host_data})

        self.assertNotIn('protocols', host_data)
        self.assertNotIn('nodes_display', host_data)
        self.assertEqual(result['name'], 'provider-one')
        self.assertEqual(result['hostname'], '192.0.2.10')

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
        provider = AppProvider(
            service_url=AppProvider.managed_service_url,
        )
        provider.__dict__['host_id'] = '00000000-0000-0000-0000-000000000001'
        host = mock.Mock()
        host.protocols.filter.return_value.exists.return_value = True
        accounts = host.accounts.active.return_value.filter.return_value
        accounts.order_by.return_value = [mock.Mock(username='root', secret='test-secret')]
        with mock.patch.object(
            AppProvider, 'host', new=mock.PropertyMock(return_value=host)
        ):
            self.assertTrue(provider.connection_ready)

        host.protocols.filter.return_value.exists.return_value = False
        with mock.patch.object(
            AppProvider, 'host', new=mock.PropertyMock(return_value=host)
        ):
            self.assertFalse(provider.connection_ready)

        host.protocols.filter.return_value.exists.return_value = True
        accounts.order_by.return_value = []
        with mock.patch.object(
            AppProvider, 'host', new=mock.PropertyMock(return_value=host)
        ):
            self.assertFalse(provider.connection_ready)

    def test_ssh_provider_requires_valid_service_url(self):
        for url in ('', 'panda:9001', 'http://127.0.0.1:invalid'):
            with self.subTest(url=url), mock.patch.object(
                AppProvider, 'host', new=mock.PropertyMock(return_value=mock.Mock())
            ):
                provider = AppProvider(service_url=url)
                self.assertFalse(provider.connection_ready)

    def test_provider_without_host_cannot_receive_connections(self):
        for url in ('', AppProvider.managed_service_url):
            with self.subTest(url=url):
                provider = AppProvider(hostname='192.0.2.10', service_url=url)
                self.assertFalse(provider.connection_ready)


class AppProviderTerminalBindingTests(TestCase):
    def setUp(self):
        self.terminal = Terminal.objects.create(name='panda', type='panda')

    def test_managed_provider_replaces_unbound_registration(self):
        legacy = AppProvider.objects.create(
            name='unbound-provider', hostname='192.0.2.10',
            terminal=self.terminal,
        )
        managed = AppProvider.objects.create(
            name='managed-ssh', hostname='192.0.2.10',
        )

        managed.bind_terminal(self.terminal)

        self.assertFalse(AppProvider.objects.filter(pk=legacy.pk).exists())
        managed.refresh_from_db()
        self.assertEqual(managed.terminal_id, self.terminal.id)

    def test_provider_does_not_take_terminal_from_another_managed_provider(self):
        from orgs.utils import tmp_to_builtin_org

        with tmp_to_builtin_org(system=1):
            serializer = AppProviderSerializer(data={'host': {
                'name': 'existing-ssh', 'address': '192.0.2.10',
            }})
            serializer.is_valid(raise_exception=True)
            serializer.save(terminal=self.terminal)
        managed = AppProvider.objects.create(
            name='managed-ssh', hostname='198.51.100.10',
        )

        with self.assertRaises(ValidationError):
            managed.bind_terminal(self.terminal)

    def test_provider_does_not_replace_its_bound_terminal(self):
        provider = AppProvider.objects.create(
            name='managed-ssh', hostname='192.0.2.10', terminal=self.terminal,
        )
        another = Terminal.objects.create(name='another-panda', type='panda')
        with self.assertRaises(ValidationError):
            provider.bind_terminal(another)

    def test_deployment_registers_and_reuses_panda_credentials(self):
        provider = AppProvider.objects.create(
            name='managed-ssh', hostname='192.0.2.10',
            terminal=self.terminal,
        )
        deployment = mock.Mock(provider=provider)
        manager = DeployAppProviderManager(deployment)

        access_key = manager.get_access_key()
        provider.refresh_from_db()

        self.assertEqual(provider.terminal.type, 'panda')
        self.assertEqual(access_key, provider.terminal.user.access_key.get_full_value())
        provider.check_terminal_binding(mock.Mock(user=provider.terminal.user))
        self.assertEqual(manager.get_access_key(), access_key)

    def test_managed_host_create_and_partial_update_preserve_ssh_port(self):
        from orgs.utils import tmp_to_builtin_org

        with tmp_to_builtin_org(system=1):
            serializer = AppProviderSerializer(data={'host': {
                'name': 'managed-ssh', 'address': '192.0.2.10',
                'protocols': [{'name': 'ssh', 'port': 2222}],
            }})
            serializer.is_valid(raise_exception=True)
            provider = serializer.save()
            update = AppProviderSerializer(
                provider, data={'host': {'comment': 'Updated'}}, partial=True,
            )
            update.is_valid(raise_exception=True)
            provider = update.save()

        self.assertEqual(provider.name, 'managed-ssh')
        self.assertEqual(provider.hostname, '192.0.2.10')
        self.assertEqual(provider.service_url, 'http://127.0.0.1:9001')
        self.assertEqual(provider.host.protocols.get(name='ssh').port, 2222)


class AppProviderCompatibilityTests(SimpleTestCase):
    def test_panda_discovers_bound_provider_using_its_service_account_id(self):
        from terminal.api.virtualapp.provider import AppProviderViewSet

        user = mock.Mock(id='service-account-id', is_service_account=True)
        provider = mock.Mock()
        view = AppProviderViewSet()
        view.request = mock.Mock(user=user)
        view.kwargs = {'pk': user.id}
        view.action = 'retrieve'
        view.get_queryset = mock.Mock()
        view.get_queryset.return_value.filter.return_value.first.return_value = provider
        view.check_object_permissions = mock.Mock()

        self.assertIs(view.get_object(), provider)
        view.get_queryset.return_value.filter.assert_called_once_with(terminal__user=user)

    def test_legacy_provider_publication_does_not_start_ansible(self):
        from terminal.api.virtualapp.virtualapp import VirtualAppPublicationViewSet

        publication = mock.Mock(provider=mock.Mock(host_id=None))
        self.assertIsNone(VirtualAppPublicationViewSet.start_publish(publication))


class AppProviderPublicationSyncTests(TestCase):
    def setUp(self):
        from orgs.utils import tmp_to_builtin_org

        with tmp_to_builtin_org(system=1):
            serializer = AppProviderSerializer(data={'host': {
                'name': 'managed-ssh', 'address': '192.0.2.10',
            }})
            serializer.is_valid(raise_exception=True)
            provider = serializer.save()
        self.app = VirtualApp.objects.create(name='app', version='2.0', image_name='example/app:v2')
        self.publication = VirtualAppPublication.objects.get(provider=provider, app=self.app)
        self.publication.app_version = '1.0'
        self.publication.save(update_fields=['app_version'])

    def report(self, data):
        from terminal.serializers import VirtualAppPublicationSerializer

        serializer = VirtualAppPublicationSerializer(
            self.publication, data=data, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def test_panda_report_cannot_publish_stale_managed_image(self):
        from terminal.serializers import VirtualAppSerializer

        update = VirtualAppSerializer(self.app, data={'version': '3.0'}, partial=True)
        update.is_valid(raise_exception=True)
        update.save()
        self.assertEqual(update.instance.image_name, 'example/app:v2')
        publication = self.report({'status': 'success'})
        self.assertEqual(publication.status, 'mismatch')

        publication.provider.host = None
        publication.provider.save(update_fields=['host'])
        publication = self.report({'status': 'success'})
        self.assertEqual(publication.status, 'success')

    def test_image_reference_change_requires_a_different_version(self):
        from terminal.serializers import VirtualAppSerializer

        for data in (
            {'image_name': 'example/app:new'},
            {'image_name': 'example/app:new', 'version': '2.0'},
        ):
            serializer = VirtualAppSerializer(self.app, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            with self.subTest(data=data), self.assertRaises(ValidationError):
                serializer.save()
        self.app.refresh_from_db()
        self.assertEqual(self.app.image_name, 'example/app:v2')

    def test_image_and_version_change_invalidates_previous_publication(self):
        from terminal.serializers import VirtualAppSerializer

        self.report({'status': 'success', 'app_version': '2.0', 'image_digest': 'sha256:current'})
        serializer = VirtualAppSerializer(self.app, data={
            'image_name': 'example/app:v3', 'version': '3.0',
        }, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'mismatch')
        self.assertEqual(self.publication.app_version, '')
        self.assertEqual(self.publication.image_digest, '')

    def test_native_panda_reports_current_version_and_digest_successfully(self):
        publication = self.report({
            'status': 'success', 'app_version': '2.0', 'image_digest': 'sha256:current',
        })
        self.assertEqual(publication.status, 'success')
        self.assertEqual(publication.app_version, '2.0')
        self.assertEqual(publication.image_digest, 'sha256:current')

    def test_outdated_success_cannot_overwrite_a_newer_success(self):
        self.report({'status': 'success', 'app_version': '2.0', 'image_digest': 'sha256:current'})
        with self.assertRaises(ValidationError):
            self.report({'status': 'success', 'app_version': '1.0', 'image_digest': 'sha256:old'})
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'success')
        self.assertEqual(self.publication.app_version, '2.0')
        self.assertEqual(self.publication.image_digest, 'sha256:current')

    def test_failed_pull_can_report_previously_observed_version(self):
        publication = self.report({
            'status': 'failed', 'app_version': '1.0', 'image_digest': 'sha256:old',
        })
        self.assertEqual(publication.status, 'failed')
        self.assertEqual(publication.app_version, '1.0')

    def test_outdated_failure_cannot_overwrite_current_success(self):
        # Keep the serializer instance stale, as when the request was loaded
        # before the current version finished publishing.
        VirtualAppPublication.objects.filter(pk=self.publication.pk).update(
            status='success', app_version='2.0', image_digest='sha256:current',
        )
        for status in ('failed', 'mismatch'):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                self.report({
                    'status': status, 'app_version': '1.0', 'image_digest': 'sha256:old',
                })
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'success')
        self.assertEqual(self.publication.app_version, '2.0')
        self.assertEqual(self.publication.image_digest, 'sha256:current')


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

        mocked_runner.return_value.run.assert_called_once_with(quiet=False, timeout=1800)

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
        ), mock.patch.object(
            DeployAppProviderManager, 'get_access_key', return_value='access-key-id:secret'
        ):
            manager = DeployAppProviderManager(deployment)
            path = manager.generate_playbook()
            with open(path) as stream:
                play = yaml.safe_load(stream)[0]
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

        variables = play['vars']
        self.assertEqual(variables['PANDA_ACCESS_KEY'], 'access-key-id:secret')
        self.assertEqual(variables['PANDA_PROVIDER_ID'], str(provider.id))
        self.assertNotIn('BOOTSTRAP_TOKEN', variables)
        self.assertEqual(variables['PANDA_HOST_IP'], '192.0.2.10')
        self.assertEqual(variables['PANDA_IMAGE'], 'jumpserver/panda:test')
        self.assertFalse(play['gather_facts'])
        self.assertEqual(play['pre_tasks'][0]['ansible.builtin.raw'], 'command -v python3')
        self.assertIn('Python 3', play['pre_tasks'][1]['ansible.builtin.assert']['fail_msg'])
        key_task = next(task for task in play['tasks'] if task['name'] == 'Configure Panda access key')
        self.assertTrue(key_task['no_log'])
        self.assertEqual(key_task['ansible.builtin.copy']['mode'], '0600')
        start_task = next(task for task in play['tasks'] if task['name'] == 'Start Panda provider')
        arguments = start_task['ansible.builtin.command']['argv']
        self.assertFalse(start_task['ansible.builtin.command']['expand_argument_vars'])
        self.assertIn('PANDA_PROVIDER_ID={{ PANDA_PROVIDER_ID }}', arguments)
        self.assertIn('PANDA_BIND_HOST=127.0.0.1', arguments)

    @mock.patch('terminal.automations.deploy_app_provider.VirtualAppPublication.objects.filter')
    @mock.patch('terminal.automations.deploy_app_provider.SuperPlaybookRunner')
    def test_successful_image_pull_finishes_publication(self, runner, publications):
        publication = mock.Mock(app=mock.Mock(version='1.0', image_name='example/app:v1'))
        deployment = mock.Mock(publication_id='publication-id', publication=publication)
        runner.return_value.run.return_value.status = 'success'
        with mock.patch.object(
            DeployAppProviderManager, 'generate_inventory', return_value='/tmp/inventory'
        ), mock.patch.object(
            DeployAppProviderManager, 'generate_playbook', return_value='/tmp/playbook'
        ):
            DeployAppProviderManager(deployment).run()

        values = publications.return_value.update.call_args.kwargs
        self.assertEqual(values['status'], 'success')
        self.assertEqual(values['app_version'], '1.0')
        self.assertIsNotNone(values['date_synced'])

    @mock.patch('terminal.automations.deploy_app_provider.VirtualAppPublication.objects.filter')
    def test_deployment_exception_only_fails_the_attempted_app_version(self, publications):
        publication = mock.Mock(app=mock.Mock(version='1.0', image_name='example/app:v1'))
        deployment = mock.Mock(publication_id='publication-id', publication=publication)
        with mock.patch.object(
            DeployAppProviderManager, 'generate_inventory', side_effect=RuntimeError('Deployment failed')
        ):
            DeployAppProviderManager(deployment).run()
        publications.assert_called_once_with(
            pk=publication.pk, app__version='1.0', app__image_name='example/app:v1',
        )
        self.assertEqual(publications.return_value.update.call_args.kwargs['status'], 'failed')

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
        self.assertFalse(play['gather_facts'])
        self.assertEqual(len(play['tasks']), 1)
        self.assertEqual(play['pre_tasks'][0]['ansible.builtin.raw'], 'command -v python3')
        self.assertEqual(
            play['tasks'][0]['ansible.builtin.command']['argv'],
            ['docker', 'pull', '{{ APP_IMAGE }}'],
        )
