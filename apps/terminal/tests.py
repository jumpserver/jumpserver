import errno
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
from compression import zstd
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from unittest.mock import Mock, patch

import yaml
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account
from assets.utils.platform_package import locate_package_root
from authentication.serializers.connect_token_secret import ConnectTokenVirtualAppOptionSerializer
from common.drf.metadata import SimpleMetadataWithFilters
from orgs.utils import tmp_to_builtin_org
from terminal.api.virtualapp.provider import AppProviderDeploymentViewSet, AppProviderViewSet
from terminal.automations.deploy_app_provider import (
    DeployAppProviderManager, default_panda_image, stage_resources,
)
from terminal.const import ComponentLoad
from terminal.models import Applet, AppProvider, AppProviderDeployment, Terminal, VirtualApp, VirtualAppPublication
from terminal.serializers import AppProviderSerializer
from terminal.serializers.virtualapp_provider import AppProviderDeployOptionsSerializer
from terminal.tasks import run_app_provider_deployment, run_app_provider_deployments
from terminal.utils import virtualapp as image_archives


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
        provider = AppProvider(name='provider-one', comment='Provider note')

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

    def test_provider_identity_matches_host(self):
        serializer = AppProviderSerializer()
        attrs = {
            'host': {'name': 'provider-one', 'address': '192.0.2.10'},
        }

        with mock.patch.object(AppProvider.objects, 'filter') as mocked_filter:
            mocked_filter.return_value.exists.return_value = False
            result = serializer.validate(attrs)

        self.assertEqual(result['name'], 'provider-one')
        self.assertNotIn('hostname', result)

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
        self.assertNotIn('hostname', result)

    def test_provider_without_host_has_no_address(self):
        provider = AppProvider()

        self.assertEqual(provider.address, '')

    def test_provider_creation_requires_host_for_regular_users(self):
        serializer = AppProviderSerializer(context={
            'request': mock.Mock(user=mock.Mock(is_service_account=False)),
        })
        with self.assertRaises(ValidationError):
            serializer.validate({'name': 'provider-one'})

    def test_address_uses_bound_host(self):
        provider = AppProvider()
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
        provider = AppProvider()
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

    def test_provider_without_host_cannot_receive_connections(self):
        provider = AppProvider()
        self.assertFalse(provider.connection_ready)


class AppProviderTerminalBindingTests(TestCase):
    def setUp(self):
        self.terminal = Terminal.objects.create(name='panda', type='panda')

    def test_managed_provider_replaces_unbound_registration(self):
        user = get_user_model().objects.create(username='legacy-panda', is_service_account=True)
        self.terminal.user = user
        self.terminal.save(update_fields=['user'])
        url = reverse('api-terminal:app-provider-list')
        incoming = APIRequestFactory().post(url, {
            'name': 'unbound-provider', 'hostname': '192.0.2.10',
        }, format='json')
        force_authenticate(incoming, user=user)
        match = resolve(url)
        response = match.func(incoming, **match.kwargs)
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('hostname', response.data)
        self.assertEqual(response.data['address'], '')
        legacy = AppProvider.objects.get(pk=user.pk)
        self.assertIsNone(legacy.host_id)
        self.assertEqual(legacy.terminal_id, self.terminal.id)
        managed = AppProvider.objects.create(
            name='managed-ssh',
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
            name='managed-ssh',
        )

        with self.assertRaises(ValidationError):
            managed.bind_terminal(self.terminal)

    def test_provider_does_not_replace_its_bound_terminal(self):
        provider = AppProvider.objects.create(
            name='managed-ssh', terminal=self.terminal,
        )
        another = Terminal.objects.create(name='another-panda', type='panda')
        with self.assertRaises(ValidationError):
            provider.bind_terminal(another)

    def test_deployment_registers_and_reuses_panda_credentials(self):
        provider = AppProvider.objects.create(
            name='managed-ssh',
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
        from terminal.api.virtualapp.provider import AppProviderFilterSet

        with tmp_to_builtin_org(system=1):
            serializer = AppProviderSerializer(data={'host': {
                'name': 'managed-ssh', 'address': '192.0.2.10',
                'protocols': [{'name': 'ssh', 'port': 2222}],
            }})
            serializer.is_valid(raise_exception=True)
            provider = serializer.save()
            update = AppProviderSerializer(
                provider, data={'host': {'comment': 'Updated'}, 'hostname': '198.51.100.20'}, partial=True,
            )
            update.is_valid(raise_exception=True)
            provider = update.save()

        self.assertEqual(provider.name, 'managed-ssh')
        self.assertEqual(provider.address, '192.0.2.10')
        self.assertEqual(provider.host.protocols.get(name='ssh').port, 2222)
        data = AppProviderSerializer(provider).data
        self.assertEqual(data['address'], '192.0.2.10')
        self.assertNotIn('hostname', data)
        self.assertEqual(list(AppProviderFilterSet({'address': '192.0.2.10'}).qs), [provider])


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

        self.report({'status': 'success', 'app_version': '2.0'})
        serializer = VirtualAppSerializer(self.app, data={
            'image_name': 'example/app:v3', 'version': '3.0',
        }, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'mismatch')
        self.assertEqual(self.publication.app_version, '')

    def test_native_panda_reports_current_version_successfully(self):
        publication = self.report({
            'status': 'success', 'app_version': '2.0',
        })
        self.assertEqual(publication.status, 'success')
        self.assertEqual(publication.app_version, '2.0')

    def test_outdated_success_cannot_overwrite_a_newer_success(self):
        VirtualAppPublication.objects.filter(pk=self.publication.pk).update(
            status='success', app_version='2.0',
        )
        self.report({'status': 'success', 'app_version': '2.0'})
        with self.assertRaises(ValidationError):
            self.report({'status': 'success', 'app_version': '1.0'})
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'success')
        self.assertEqual(self.publication.app_version, '2.0')

    def test_failed_pull_can_report_previously_observed_version(self):
        publication = self.report({
            'status': 'failed', 'app_version': '1.0',
        })
        self.assertEqual(publication.status, 'failed')
        self.assertEqual(publication.app_version, '1.0')

    def test_outdated_failure_cannot_overwrite_current_success(self):
        # Keep the serializer instance stale, as when the request was loaded
        # before the current version finished publishing.
        VirtualAppPublication.objects.filter(pk=self.publication.pk).update(
            status='success', app_version='2.0',
        )
        for status in ('failed', 'mismatch'):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                self.report({
                    'status': status, 'app_version': '1.0',
                })
        self.publication.refresh_from_db()
        self.assertEqual(self.publication.status, 'success')
        self.assertEqual(self.publication.app_version, '2.0')

    def test_reports_without_version_preserve_known_publication(self):
        VirtualAppPublication.objects.filter(pk=self.publication.pk).update(
            status='failed', app_version='2.0',
        )
        for status in ('pending', 'failed', 'success'):
            with self.subTest(status=status):
                publication = self.report({'status': status})
                self.assertEqual(publication.status, 'failed')
                self.assertEqual(publication.app_version, '2.0')

    @mock.patch('terminal.automations.deploy_app_provider.safe_db_connection', new=nullcontext)
    def test_late_ssh_result_cannot_overwrite_a_completed_panda_pull(self):
        for outcome in ('success', 'failed', 'error'):
            with self.subTest(outcome=outcome):
                VirtualAppPublication.objects.filter(pk=self.publication.pk).update(
                    status='pending', app_version='',
                )
                deployment = AppProviderDeployment.objects.create(
                    provider=self.publication.provider, publication=self.publication,
                )

                def finish_pull(*args, **kwargs):
                    self.report({'status': 'success', 'app_version': self.app.version})
                    if outcome == 'error':
                        raise RuntimeError('SSH verification failed')
                    return mock.Mock(status='successful' if outcome == 'success' else outcome)

                with mock.patch.object(
                    DeployAppProviderManager, 'generate_inventory', return_value='/tmp/inventory'
                ), mock.patch.object(
                    DeployAppProviderManager, 'generate_playbook', return_value='/tmp/playbook'
                ), mock.patch('terminal.automations.deploy_app_provider.SuperPlaybookRunner') as runner:
                    runner.return_value.run.side_effect = finish_pull
                    DeployAppProviderManager(deployment).run()
                deployment.refresh_from_db()
                self.publication.refresh_from_db()
                self.assertEqual(deployment.status, outcome)
                self.assertEqual(self.publication.status, 'success')
                self.assertEqual(self.publication.app_version, self.app.version)


class AppProviderDeployOptionsTests(SimpleTestCase):
    def test_deploy_options_validate_and_normalize(self):
        serializer = AppProviderDeployOptionsSerializer(data={
            'CORE_HOST': 'https://core.example.com/',
            'PANDA_IMAGE': 'registry.example.com:5000/team/panda:v4.0',
            'PANDA_RANGE_PORTS': '6900-7900',
        })
        serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.validated_data['CORE_HOST'], 'https://core.example.com')
        self.assertEqual(serializer.validated_data['PANDA_IMAGE'], 'registry.example.com:5000/team/panda:v4.0')

    def test_invalid_deploy_options_are_rejected(self):
        invalid = {
            'CORE_HOST': ('', 'ssh://core.example.com', 'https://user:secret@core.example.com',
                          'http://core.example.com:65536', 'http://core.example.com?token=secret'),
            'PANDA_IMAGE': ('--privileged', 'panda:latest;id', 'panda image', 'panda@sha256:abc'),
            'PANDA_RANGE_PORTS': ('0-10', '7900-6900', '6900-6900', '9000-9100', '60000-65536'),
        }
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    serializer = AppProviderDeployOptionsSerializer(data={
                        'CORE_HOST': 'https://core.example.com', field: value,
                    })
                    self.assertFalse(serializer.is_valid())
                    self.assertIn(field, serializer.errors)


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
        self.assertEqual(variables['PANDA_IMAGE'], 'jumpserver/panda:test')
        self.assertEqual(variables['PANDA_RANGE_PORTS'], '7000-7100')
        self.assertTrue(variables['IGNORE_VERIFY_CERTS'])
        self.assertFalse(play['gather_facts'])
        self.assertEqual(play['pre_tasks'][0]['ansible.builtin.raw'], 'command -v python3')
        key_task = next(task for task in play['tasks'] if task['name'] == 'Configure Panda access key')
        self.assertTrue(key_task['no_log'])
        self.assertEqual(key_task['ansible.builtin.copy']['mode'], '0600')
        start_task = next(task for task in play['tasks'] if task['name'] == 'Start Panda provider')
        arguments = start_task['ansible.builtin.command']['argv']
        self.assertFalse(start_task['ansible.builtin.command']['expand_argument_vars'])
        self.assertIn('PANDA_PROVIDER_ID={{ PANDA_PROVIDER_ID }}', arguments)
        self.assertIn('PANDA_BIND_HOST=127.0.0.1', arguments)
        self.assertIn('--pull=never', arguments)
        self.assertEqual(arguments[-1], '{{ provider_image.Id }}')

    @mock.patch('terminal.automations.deploy_app_provider.VirtualAppPublication.objects.filter')
    @mock.patch('terminal.automations.deploy_app_provider.SuperPlaybookRunner')
    def test_confirmed_local_image_finishes_publication(self, runner, publications):
        publication = mock.Mock(app=mock.Mock(version='1.0', image_name='example/app:v1'))
        deployment = mock.Mock(publication_id='publication-id', publication=publication)
        runner.return_value.run.return_value.status = 'success'
        with mock.patch.object(
            DeployAppProviderManager, 'generate_inventory', return_value='/tmp/inventory'
        ), mock.patch.object(
            DeployAppProviderManager, 'generate_playbook', return_value='/tmp/playbook'
        ):
            DeployAppProviderManager(deployment).run()

        values = publications.return_value.exclude.return_value.update.call_args.kwargs
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
        self.assertEqual(publications.return_value.exclude.return_value.update.call_args.kwargs['status'], 'failed')

    @override_settings(SITE_URL='https://core.example.com', BOOTSTRAP_TOKEN='token')
    def test_publish_playbook_confirms_preloaded_virtual_app_image(self):
        provider = mock.Mock(
            id='00000000-0000-0000-0000-000000000010',
            host=mock.Mock(address='192.0.2.10'),
            deploy_options={
                'CORE_HOST': 'https://core.example.com',
                'PANDA_IMAGE': 'jumpserver/panda:test',
                'PANDA_RANGE_PORTS': '7000-7100',
                'IGNORE_VERIFY_CERTS': False,
            },
        )
        provider.name = 'provider-one'
        publication = mock.Mock(app=mock.Mock(image_name='example/app:v1', version='1.0'))
        deployment = mock.Mock(
            provider=provider, publication_id='publication-id', publication=publication,
        )
        with tempfile.TemporaryDirectory() as ansible_dir, override_settings(
            ANSIBLE_DIR=ansible_dir
        ), mock.patch(
            'terminal.automations.deploy_app_provider.stage_image_archives', return_value={}
        ):
            path = DeployAppProviderManager(deployment).generate_playbook()
            with open(path) as stream:
                play = yaml.safe_load(stream)[0]

        self.assertEqual(play['vars'], {'APP_IMAGE': 'example/app:v1', 'APP_IMAGE_RESOURCES': {}})
        self.assertFalse(play['gather_facts'])
        self.assertNotIn('pre_tasks', play)
        self.assertIn('ansible.builtin.assert', play['tasks'][-1])


class AppProviderDeploymentAPITests(TestCase):
    def setUp(self):
        self.enterContext(tmp_to_builtin_org(system=1))
        self.cache = self.enterContext(mock.patch('terminal.models.virtualapp.provider.cache'))
        self.cache.get.return_value = []
        serializer = AppProviderSerializer(data={
            'host': {'name': 'managed-provider', 'address': '192.0.2.10'},
            'deploy_options': {
                'CORE_HOST': 'https://core.example.com', 'PANDA_IMAGE': 'jumpserver/panda:test',
            },
        })
        serializer.is_valid(raise_exception=True)
        self.provider = serializer.save()
        self.account = Account.objects.create(
            asset=self.provider.host, name='root', username='root', secret='test-secret',
        )

    def create_deployment(self):
        view = AppProviderDeploymentViewSet()
        view.request = SimpleNamespace(data={'provider': str(self.provider.id)})
        view.format_kwarg = None
        return view.create(view.request)

    def test_connection_options_include_ssh_host_and_account(self):
        data = ConnectTokenVirtualAppOptionSerializer.get_provider({'provider': self.provider})

        self.assertEqual(set(data), {
            'id', 'name', 'address', 'host_id',
            'load', 'host', 'account', 'gateway',
        })
        self.assertEqual(data['host']['address'], self.provider.host.address)
        self.assertEqual(data['host']['protocols'][0]['name'], 'ssh')
        self.assertEqual(data['account']['username'], 'root')
        self.assertEqual(data['account']['secret'], 'test-secret')

    def test_connection_options_reject_missing_host_or_ssh_account(self):
        with self.assertRaisesMessage(ValidationError, 'provider is required'):
            ConnectTokenVirtualAppOptionSerializer.get_provider({})

        with self.assertRaisesMessage(ValidationError, 'SSH host'):
            ConnectTokenVirtualAppOptionSerializer.get_provider({'provider': AppProvider()})

        self.account.is_active = False
        self.account.save(update_fields=['is_active'])
        with self.assertRaisesMessage(ValidationError, 'SSH account'):
            ConnectTokenVirtualAppOptionSerializer.get_provider({'provider': self.provider})

    def test_failed_worker_is_reported_and_duplicate_delivery_does_not_redeploy(self):
        deployment = AppProviderDeployment.objects.create(provider=self.provider)

        def fail(instance):
            instance.status = 'failed'
            instance.save(update_fields=['status'])

        with mock.patch.object(AppProviderDeployment, 'start', autospec=True, side_effect=fail) as start:
            with self.assertRaisesMessage(RuntimeError, 'deployment failed'):
                run_app_provider_deployment(str(deployment.id))
            run_app_provider_deployment(str(deployment.id))
        self.assertEqual(start.call_count, 1)

    def test_batch_attempts_remaining_deployments_and_reports_failure(self):
        deployments = [AppProviderDeployment.objects.create(provider=self.provider) for _ in range(2)]

        def finish(instance):
            instance.status = 'failed' if instance.pk == deployments[0].pk else 'success'
            instance.save(update_fields=['status'])

        with mock.patch.object(AppProviderDeployment, 'start', autospec=True, side_effect=finish) as start:
            with self.assertRaisesMessage(RuntimeError, str(deployments[0].id)):
                run_app_provider_deployments([str(item.id) for item in deployments])
        self.assertEqual(start.call_count, 2)
        deployments[1].refresh_from_db()
        self.assertEqual(deployments[1].status, 'success')

    @mock.patch('terminal.automations.deploy_app_provider.safe_db_connection', new=nullcontext)
    def test_worker_preserves_claimed_start_time_on_a_preloaded_deployment(self):
        deployment = AppProviderDeployment.objects.create(provider=self.provider)
        claimed_start = timezone.now()
        # Batch workers load deployment objects before the atomic task claim.
        AppProviderDeployment.objects.filter(pk=deployment.pk).update(
            status='running', date_start=claimed_start,
        )
        with mock.patch.object(
            DeployAppProviderManager, 'generate_inventory', return_value='/tmp/inventory'
        ), mock.patch.object(
            DeployAppProviderManager, 'generate_playbook', return_value='/tmp/playbook'
        ), mock.patch('terminal.automations.deploy_app_provider.SuperPlaybookRunner') as runner:
            runner.return_value.run.return_value.status = 'successful'
            DeployAppProviderManager(deployment).run()
        deployment.refresh_from_db()
        self.assertEqual(deployment.date_start, claimed_start)
        self.assertEqual(deployment.status, 'success')
        self.assertIsNotNone(deployment.date_finished)

    def test_maintenance_host_can_deploy_but_cannot_receive_connections(self):
        self.provider.host.is_active = False
        self.provider.host.save(update_fields=['is_active'])
        self.assertEqual(self.provider.validate_deployment()['PANDA_RANGE_PORTS'], '6900-7900')
        self.assertFalse(self.provider.connection_ready)

    def test_missing_bundle_and_unspecified_panda_image_use_core_version(self):
        from django.test import override_settings

        self.provider.deploy_options.pop('PANDA_IMAGE')
        with tempfile.TemporaryDirectory() as data_dir, override_settings(DATA_DIR=data_dir, VERSION='dev'):
            self.assertEqual(self.provider.validate_deployment()['PANDA_IMAGE'], 'jumpserver/panda:dev')

    def test_invalid_offline_manifest_is_exposed_as_deployment_error(self):
        from pathlib import Path
        from django.test import override_settings

        with tempfile.TemporaryDirectory() as data_dir, override_settings(DATA_DIR=data_dir):
            resources = Path(data_dir) / 'virtualapp'
            resources.mkdir()
            (resources / 'manifest.json').write_text('{invalid')
            error = AppProviderSerializer.get_deployment_error(self.provider)
        self.assertIn('Invalid offline deployment resources', error)

    def test_deployment_api_rejects_invalid_account_and_reserved_ssh_port(self):
        self.account.secret = ''
        self.account.save()
        with self.assertRaisesMessage(ValidationError, 'SSH account'):
            self.create_deployment()
        self.account.secret = 'test-secret'
        self.account.save()
        self.provider.host.protocols.filter(name='ssh').update(port=6900)
        with self.assertRaisesMessage(ValidationError, 'SSH port'):
            self.create_deployment()
        self.assertFalse(AppProviderDeployment.objects.filter(provider=self.provider).exists())

    def test_live_containers_block_deployment(self):
        self.cache.get.return_value = [{'container_id': 'running-container'}]
        with self.assertRaisesMessage(ValidationError, 'containers to exit'):
            self.provider.validate_deployment()

    def test_ssh_account_selection_skips_unusable_credentials(self):
        Account.objects.create(
            asset=self.provider.host, name='empty-key', username='operator',
            secret_type='ssh_key', privileged=True,
        )
        Account.objects.create(
            asset=self.provider.host, name='token', username='operator',
            secret_type='token', secret='test-token', privileged=True,
        )
        self.assertEqual(self.provider.select_account().pk, self.account.pk)
        self.assertEqual(self.provider.select_deploy_account().pk, self.account.pk)
        self.account.is_active = False
        self.account.save(update_fields=['is_active'])
        self.assertIsNone(self.provider.select_account())
        self.assertFalse(self.provider.connection_ready)

    def test_disabled_provider_inventory_has_only_the_remote_ssh_target(self):
        self.provider.host.is_active = False
        self.provider.host.save(update_fields=['is_active'])
        deployment = AppProviderDeployment(provider=self.provider)
        with tempfile.TemporaryDirectory() as run_dir:
            manager = DeployAppProviderManager(deployment)
            manager.run_dir = run_dir
            with open(manager.generate_inventory()) as stream:
                hosts = json.load(stream)['all']['hosts']
        self.assertEqual(len(hosts), 1)
        self.assertNotIn('localhost', hosts)
        host = next(iter(hosts.values()))
        self.assertEqual(host['ansible_connection'], 'ssh')
        self.assertEqual(host['ansible_host'], self.provider.host.address)
        self.assertEqual(host['jms_asset']['id'], str(self.provider.host.id))

    def test_privileged_password_account_inventory_uses_sudo_to_root(self):
        self.account.username = 'operator'
        self.account.privileged = True
        self.account.save()
        deployment = AppProviderDeployment(provider=self.provider)
        with tempfile.TemporaryDirectory() as run_dir:
            manager = DeployAppProviderManager(deployment)
            manager.run_dir = run_dir
            with open(manager.generate_inventory()) as stream:
                hosts = json.load(stream)['all']['hosts']
        host = next(iter(hosts.values()))
        self.assertTrue(host['ansible_become'])
        self.assertEqual(host['ansible_become_method'], 'sudo')
        self.assertEqual(host['ansible_become_user'], 'root')
        self.assertEqual(host['ansible_become_password'], self.account.secret)

    def test_duplicate_deployment_is_rejected_and_failed_deployment_can_retry(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.create_deployment()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['task'], response.data['id'])
        self.assertEqual(len(callbacks), 1)
        self.assertFalse(self.provider.connection_ready)
        with self.assertRaisesMessage(ValidationError, 'already pending or running'):
            self.create_deployment()
        AppProviderDeployment.objects.filter(provider=self.provider).update(status='failed')
        self.assertFalse(self.provider.connection_ready)
        with self.captureOnCommitCallbacks(execute=False):
            retry = self.create_deployment()
        self.assertNotEqual(response.data['id'], retry.data['id'])
        AppProviderDeployment.objects.filter(pk=retry.data['id']).update(status='success')
        self.assertTrue(self.provider.connection_ready)

    def test_dispatch_failure_records_error_and_allows_retry(self):
        with mock.patch('terminal.api.virtualapp.provider.run_app_provider_deployment.apply_async',
                        side_effect=RuntimeError('Broker unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'Broker unavailable'):
                with self.captureOnCommitCallbacks(execute=True):
                    self.create_deployment()
        deployment = self.provider.latest_deployment
        self.assertEqual(deployment.status, 'error')
        self.assertIsNotNone(deployment.date_finished)
        with self.captureOnCommitCallbacks(execute=False):
            self.assertEqual(self.create_deployment().status_code, 201)

    def test_provider_reports_deployment_and_rejects_edits_while_running(self):
        with self.captureOnCommitCallbacks(execute=False):
            response = self.create_deployment()
        data = AppProviderSerializer(self.provider).data
        self.assertEqual(data['deployment']['task'], response.data['task'])
        self.assertEqual(data['deployment']['status']['value'], 'pending')
        self.assertEqual(data['deployment_error'], '')
        serializer = AppProviderSerializer(self.provider, data={'comment': 'edit'}, partial=True)
        serializer.is_valid(raise_exception=True)
        with self.assertRaisesMessage(ValidationError, 'current deployment'):
            serializer.save()

    def test_provider_delete_and_bulk_delete_reject_unfinished_deployments(self):
        deployment = AppProviderDeployment.objects.create(provider=self.provider)
        view = AppProviderViewSet()
        with self.assertRaisesMessage(ValidationError, 'current deployment'):
            view.perform_destroy(self.provider)
        idle = AppProvider.objects.create(
            id='00000000-0000-0000-0000-000000000001', name='idle-provider',
        )
        providers = AppProvider.objects.filter(pk__in=[idle.pk, self.provider.pk])
        with self.assertRaisesMessage(ValidationError, 'current deployment'):
            view.perform_bulk_destroy(providers)
        self.assertEqual(providers.count(), 2)
        deployment.status = 'success'
        deployment.save(update_fields=['status'])
        view.perform_destroy(self.provider)
        self.assertFalse(AppProvider.objects.filter(pk=self.provider.pk).exists())


class OfflineProviderResourcesTests(SimpleTestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(override_settings(DATA_DIR=self.directory, VERSION='v5.0.1-ee'))
        self.resources = Path(self.directory) / 'virtualapp'
        self.resources.mkdir()
        self.image = 'jumpserver/panda:v5.0-ee'
        self.metadata = {
            'image': self.image, 'architecture': 'amd64',
            'image_id': 'sha256:' + '1' * 64, 'sha256': '2' * 64, 'file': 'panda.zst',
        }

    def write_manifest(self):
        (self.resources / 'manifest.json').write_text(json.dumps({'panda': self.metadata}))

    def test_missing_bundle_uses_core_version(self):
        self.assertEqual(default_panda_image(), 'jumpserver/panda:v5.0.1-ee')
        self.assertEqual(stage_resources(Path(self.directory) / 'task', self.image), {'panda': {}, 'docker': {}})

    def test_malformed_manifest_keeps_form_readable_but_blocks_staging(self):
        (self.resources / 'manifest.json').write_text('{invalid')
        self.assertEqual(default_panda_image(), '')
        with self.assertRaises(ValueError):
            stage_resources(Path(self.directory) / 'task', self.image)

    def test_options_default_and_cleared_override_use_exact_bundle_image(self):
        metadata = SimpleMetadataWithFilters()
        field = AppProviderDeployOptionsSerializer().fields['PANDA_IMAGE']
        self.assertEqual(metadata.get_field_info(field).get('default'), 'jumpserver/panda:v5.0.1-ee')
        self.write_manifest()
        fields = metadata.get_serializer_info(AppProviderSerializer())
        self.assertEqual(fields['deploy_options']['children']['PANDA_IMAGE']['default'], self.image)
        for options in ({}, {'PANDA_IMAGE': ''}):
            serializer = AppProviderDeployOptionsSerializer(data={
                'CORE_HOST': 'https://core.example.com', **options,
            })
            serializer.is_valid(raise_exception=True)
            self.assertEqual(serializer.validated_data['PANDA_IMAGE'], self.image)

    def test_staged_archive_remains_readable_after_installer_replaces_source(self):
        self.write_manifest()
        source = self.resources / 'panda.zst'
        source.write_bytes(b'offline archive')
        staged = stage_resources(Path(self.directory) / 'task', self.image)['panda']
        self.assertEqual(os.stat(staged['file']).st_ino, source.stat().st_ino)
        replacement = self.resources / 'new.zst'
        replacement.write_bytes(b'new archive')
        os.replace(replacement, source)
        self.assertEqual(Path(staged['file']).read_bytes(), b'offline archive')
        staged = stage_resources(Path(self.directory) / 'next-task', self.image)['panda']
        source.unlink()
        self.assertEqual(Path(staged['file']).read_bytes(), b'new archive')

    def test_archive_removed_during_staging_preserves_identity_for_local_reuse(self):
        self.write_manifest()
        source = self.resources / 'panda.zst'
        link, copyfile = os.link, shutil.copyfile

        for cross_device in (False, True):
            with self.subTest(cross_device=cross_device):
                source.write_bytes(b'offline archive')

                def stage_archive(src, dst):
                    source.unlink()
                    return (copyfile if cross_device else link)(src, dst)

                with mock.patch('os.link', side_effect=(
                    OSError(errno.EXDEV, 'Cross-device link') if cross_device else stage_archive
                )), mock.patch('shutil.copyfile', side_effect=stage_archive):
                    staged = stage_resources(Path(self.directory) / 'task', self.image)['panda']

                self.assertEqual(staged, {**self.metadata, 'file': ''})

    def test_staging_does_not_ignore_other_io_errors(self):
        self.write_manifest()
        (self.resources / 'panda.zst').write_bytes(b'offline archive')
        with mock.patch('os.link', side_effect=PermissionError('Permission denied')):
            with self.assertRaises(PermissionError):
                stage_resources(Path(self.directory) / 'task', self.image)

    def test_missing_archive_preserves_identity_for_local_reuse(self):
        self.write_manifest()
        staged = stage_resources(Path(self.directory) / 'task', self.image)['panda']
        self.assertEqual(staged['file'], '')
        self.assertEqual(staged['image_id'], self.metadata['image_id'])

    def test_docker_service_snapshot_survives_installer_updates(self):
        metadata = {'architecture': 'amd64', 'sha256': '3' * 64, 'file': 'docker.tar.gz'}
        (self.resources / 'manifest.json').write_text(json.dumps({'docker': metadata}))
        (self.resources / 'docker.tar.gz').write_bytes(b'docker archive')
        service = self.resources / 'docker.service'
        link = os.link
        for cross_device in (False, True):
            with self.subTest(cross_device=cross_device):
                service.write_bytes(b'installer service')
                with mock.patch('os.link', side_effect=(
                    OSError(errno.EXDEV, 'Cross-device link') if cross_device else link
                )):
                    staged = stage_resources(
                        Path(self.directory) / f'task-{cross_device}', self.image,
                    )['docker']
                replacement = self.resources / 'new.service'
                replacement.write_bytes(b'updated installer service')
                os.replace(replacement, service)
                self.assertEqual(Path(staged['service']).read_bytes(), b'installer service')
                self.assertEqual(Path(staged['file']).read_bytes(), b'docker archive')

    def test_missing_docker_service_keeps_archive_available_for_runtime_check(self):
        metadata = {'architecture': 'amd64', 'sha256': '3' * 64, 'file': 'docker.tar.gz'}
        (self.resources / 'manifest.json').write_text(json.dumps({'docker': metadata}))
        (self.resources / 'docker.tar.gz').write_bytes(b'docker archive')
        staged = stage_resources(Path(self.directory) / 'task', self.image)['docker']
        self.assertEqual(staged['service'], '')
        self.assertEqual(Path(staged['file']).read_bytes(), b'docker archive')

    def test_custom_image_does_not_use_bundle_identity(self):
        self.write_manifest()
        staged = stage_resources(Path(self.directory) / 'task', 'custom/panda:v1')
        self.assertEqual(staged['panda'], {})

    def test_archive_path_cannot_escape_resource_directory(self):
        self.metadata['file'] = '../outside.zst'
        self.write_manifest()
        with self.assertRaisesMessage(ValueError, 'archive path'):
            stage_resources(Path(self.directory) / 'task', self.image)


class VirtualAppImageArchiveTests(TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(override_settings(DATA_DIR=self.directory, ANSIBLE_DIR=self.directory))
        self.app = VirtualApp.objects.create(name='offline-image', version='1.0', image_name='alpine:3.20')

    @staticmethod
    def make_archive(architecture='amd64', compressed=False, tag='docker.io/library/alpine:3.20',
                     system='linux', extra=(), blobs=False):
        config = json.dumps({'os': system, 'architecture': architecture, 'rootfs': {'type': 'layers', 'diff_ids': []}}).encode()
        name = hashlib.sha256(config).hexdigest()
        name = 'blobs/sha256/' + name if blobs else name + '.json'
        manifest = json.dumps([{'Config': name, 'RepoTags': [tag], 'Layers': []}]).encode()
        entries = [(name, config), ('manifest.json', manifest), *extra]
        if blobs:
            descriptor = json.dumps({
                'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                'config': {'mediaType': 'application/vnd.oci.image.config.v1+json',
                           'digest': 'sha256:' + hashlib.sha256(config).hexdigest(), 'size': len(config)},
                'layers': [],
            }).encode()
            digest = 'sha256:' + hashlib.sha256(descriptor).hexdigest()
            index = json.dumps({'schemaVersion': 2, 'manifests': [{'digest': digest}]}).encode()
            entries += [
                ('blobs/' + digest.replace(':', '/'), descriptor),
                ('blobs/sha256/' + hashlib.sha256(index).hexdigest(), index),
                ('index.json', index),
            ]
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for filename, data in entries:
                member = tarfile.TarInfo(filename)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        data = stream.getvalue()
        return SimpleUploadedFile('image.TAR.ZST' if compressed else 'image.tar', zstd.compress(data) if compressed else data)

    def test_tar_and_zstd_preserve_bytes_and_stage_both_platforms(self):
        for architecture, compressed in [('amd64', False), ('arm64', True)]:
            upload = self.make_archive(architecture, compressed=compressed, blobs=compressed)
            payload = upload.read()
            metadata = image_archives.save_image_archive(self.app, upload)
            self.assertEqual(metadata['sha256'], hashlib.sha256(payload).hexdigest())
            self.assertEqual((image_archives.archive_root(self.app) / metadata['file']).read_bytes(), payload)
            self.assertEqual(len(metadata['image_ids']), 2 if compressed else 1)
        resources = image_archives.stage_image_archives(self.app, Path(self.directory) / 'task')
        self.assertEqual(set(resources), {'amd64', 'arm64'})
        self.assertEqual(resources['arm64']['image_ids'], metadata['image_ids'])
        for architecture, image in resources.items():
            source = image_archives.archive_root(self.app) / Path(image['file']).name
            self.assertEqual(source.stat().st_ino, Path(image['file']).stat().st_ino)
        deployment = mock.Mock(publication_id='publication', publication=mock.Mock(app=self.app))
        with open(DeployAppProviderManager(deployment).generate_playbook()) as stream:
            variables = yaml.safe_load(stream)[0]['vars']
        self.assertEqual(set(variables['APP_IMAGE_RESOURCES']), {'amd64', 'arm64'})

    def test_oci_manifest_id_must_reference_the_selected_config(self):
        descriptor = json.dumps({
            'schemaVersion': 2, 'config': {'digest': 'sha256:' + '0' * 64}, 'layers': [],
        }).encode()
        digest = 'sha256:' + hashlib.sha256(descriptor).hexdigest()
        image = image_archives.save_image_archive(self.app, self.make_archive(
            blobs=True, extra=[('blobs/' + digest.replace(':', '/'), descriptor)],
        ))
        self.assertEqual(len(image['image_ids']), 2)
        self.assertNotIn(digest, image['image_ids'])

    def test_invalid_upload_preserves_previous_archive(self):
        image = image_archives.save_image_archive(self.app, self.make_archive())
        for upload in [
            SimpleUploadedFile('invalid.zst', b'invalid archive'),
            self.make_archive(tag='private.example.com/library/alpine:3.20'),
            self.make_archive(tag='alpine:other'),
            self.make_archive(system='windows'),
            self.make_archive(extra=[('manifest.json', b'[]')]),
            self.make_archive(extra=[('../outside', b'escape')]),
        ]:
            with self.subTest(filename=upload.name), self.assertRaises(ValidationError):
                image_archives.save_image_archive(self.app, upload)
            self.assertEqual(image_archives.get_image_archives(self.app), [image])
        with mock.patch.object(image_archives, 'MAX_SCAN_SIZE', 1), self.assertRaises(ValidationError):
            image_archives.save_image_archive(self.app, self.make_archive())
        self.assertEqual(set(path.name for path in image_archives.archive_root(self.app).iterdir()), {'manifest.json', image['file']})

    def test_replace_delete_and_app_delete_preserve_staged_files(self):
        image = image_archives.save_image_archive(self.app, self.make_archive())
        staged = image_archives.stage_image_archives(self.app, Path(self.directory) / 'task')['amd64']
        payload = Path(staged['file']).read_bytes()
        replacement = image_archives.save_image_archive(self.app, self.make_archive(compressed=True))
        self.assertFalse((image_archives.archive_root(self.app) / image['file']).exists())
        image_archives.save_image_archive(self.app, self.make_archive('arm64'))
        image_archives.delete_image_archive(self.app, 'amd64')
        self.assertFalse((image_archives.archive_root(self.app) / replacement['file']).exists())
        root = image_archives.archive_root(self.app)
        with self.captureOnCommitCallbacks(execute=True):
            self.app.delete()
        self.assertFalse(root.exists())
        self.assertEqual(Path(staged['file']).read_bytes(), payload)

    def test_missing_and_outdated_archives_allow_online_fallback(self):
        self.assertEqual(image_archives.stage_image_archives(self.app, self.directory), {})
        image = image_archives.save_image_archive(self.app, self.make_archive())
        source = image_archives.archive_root(self.app) / image['file']
        source.unlink()
        self.assertEqual(image_archives.stage_image_archives(self.app, self.directory), {})
        image_archives.save_image_archive(self.app, self.make_archive())
        self.app.version = '2.0'
        self.app.save(update_fields=['version'])
        self.assertEqual(image_archives.stage_image_archives(self.app, self.directory), {})
        self.assertEqual(image_archives.get_image_archives(self.app)[0]['version'], '1.0')

    def test_upload_version_race_and_manifest_failure_keep_previous_resources(self):
        image = image_archives.save_image_archive(self.app, self.make_archive())
        with mock.patch.object(image_archives, '_write_manifest', side_effect=OSError('Disk full')):
            with self.assertRaises(OSError):
                image_archives.save_image_archive(self.app, self.make_archive(compressed=True))
        self.assertEqual(image_archives.get_image_archives(self.app), [image])
        inspect = image_archives._inspect_archive

        def change_version(*args):
            result = inspect(*args)
            VirtualApp.objects.filter(pk=self.app.pk).update(version='2.0')
            return result

        with mock.patch.object(image_archives, '_inspect_archive', side_effect=change_version):
            with self.assertRaisesMessage(ValidationError, 'changed'):
                image_archives.save_image_archive(self.app, self.make_archive(compressed=True))
        self.assertEqual(image_archives.get_image_archives(self.app), [image])

    def test_cross_device_stage_keeps_open_source_during_replacement(self):
        image = image_archives.save_image_archive(self.app, self.make_archive())
        source = image_archives.archive_root(self.app) / image['file']
        payload, copyfileobj = source.read_bytes(), shutil.copyfileobj

        def replace_source(opened, output, length):
            source.unlink()
            copyfileobj(opened, output, length)

        with mock.patch.object(image_archives.os, 'link', side_effect=OSError(errno.EXDEV, 'Cross-device')):
            with mock.patch.object(image_archives.shutil, 'copyfileobj', side_effect=replace_source):
                resources = image_archives.stage_image_archives(self.app, Path(self.directory) / 'task')
        self.assertEqual(Path(resources['amd64']['file']).read_bytes(), payload)

    def test_image_api_permissions_upload_and_architecture_delete(self):
        user = get_user_model().objects.create(username='image-upload-user')
        permissions = {'terminal.view_virtualapp'}
        user.has_perms = lambda required: set(required).issubset(permissions)
        url = reverse('api-terminal:virtual-app-images', kwargs={'pk': self.app.pk})
        match = resolve(url)
        factory = APIRequestFactory()

        def request(method, data=None, suffix=''):
            incoming = getattr(factory, method)(url + suffix, data or {}, format='multipart')
            force_authenticate(incoming, user=user)
            with transaction.atomic():
                return match.func(incoming, **match.kwargs)

        self.assertEqual(request('get').status_code, 200)
        self.assertEqual(request('post', {'file': self.make_archive()}).status_code, 403)
        self.assertEqual(request('delete', suffix='?architecture=amd64').status_code, 403)
        permissions.add('terminal.change_virtualapp')
        for architecture in ('amd64', 'arm64'):
            response = request('post', {'file': self.make_archive(architecture)})
            self.assertEqual(response.status_code, 201)
        before = response.data
        self.assertEqual(before['max_size'], image_archives.MAX_IMAGE_SIZE)
        self.assertEqual(set(before['images'][0]), {'filename', 'size', 'version', 'image_name', 'os', 'architecture'})
        self.assertEqual(request('post', {'file': SimpleUploadedFile('bad.tar', b'bad')}).status_code, 400)
        self.assertEqual(request('get').data, before)
        self.assertEqual(request('delete').status_code, 400)
        response = request('delete', suffix='?architecture=amd64')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([image['architecture'] for image in response.data['images']], ['arm64'])
