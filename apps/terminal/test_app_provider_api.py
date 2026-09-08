import json
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from accounts.models import Account
from authentication.serializers.connect_token_secret import ConnectTokenVirtualAppOptionSerializer
from orgs.utils import tmp_to_builtin_org
from terminal.api.virtualapp.provider import AppProviderDeploymentViewSet, AppProviderViewSet
from terminal.automations.deploy_app_provider import DeployAppProviderManager
from terminal.models import AppProvider, AppProviderDeployment
from terminal.serializers import AppProviderSerializer
from terminal.serializers.virtualapp_provider import AppProviderDeployOptionsSerializer
from terminal.tasks import run_app_provider_deployment, run_app_provider_deployments


class AppProviderDeployOptionsTests(SimpleTestCase):
    def test_deploy_options_validate_and_normalize(self):
        serializer = AppProviderDeployOptionsSerializer(data={
            'CORE_HOST': 'https://core.example.com/',
            'PANDA_IMAGE': 'registry.example.com:5000/team/panda:v4.0',
            'PANDA_RANGE_PORTS': '6900-7900',
        })
        serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.validated_data['CORE_HOST'], 'https://core.example.com')

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


class AppProviderDeploymentAPITests(TestCase):
    def setUp(self):
        self.enterContext(tmp_to_builtin_org(system=1))
        self.cache = self.enterContext(mock.patch('terminal.models.virtualapp.provider.cache'))
        self.cache.get.return_value = []
        serializer = AppProviderSerializer(data={
            'host': {'name': 'managed-provider', 'address': '192.0.2.10'},
            'deploy_options': {'CORE_HOST': 'https://core.example.com'},
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
            'id', 'name', 'hostname', 'address', 'host_id', 'runtime_type',
            'service_url', 'load', 'host', 'account', 'gateway',
        })
        self.assertEqual(data['host']['address'], self.provider.host.address)
        self.assertEqual(data['host']['protocols'][0]['name'], 'ssh')
        self.assertEqual(data['account']['username'], 'root')
        self.assertEqual(data['account']['secret'], 'test-secret')
        self.assertEqual(data['service_url'], 'http://127.0.0.1:9001')

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

    def test_maintenance_host_can_deploy_but_cannot_receive_connections(self):
        self.provider.host.is_active = False
        self.provider.host.save(update_fields=['is_active'])
        self.assertEqual(self.provider.validate_deployment()['PANDA_RANGE_PORTS'], '6900-7900')
        self.assertFalse(self.provider.connection_ready)

    def test_invalid_account_and_reserved_ssh_port_block_deployment(self):
        self.account.secret = ''
        self.account.save()
        with self.assertRaisesMessage(ValidationError, 'SSH account'):
            self.provider.validate_deployment()
        self.account.secret = 'test-secret'
        self.account.save()
        self.provider.host.protocols.filter(name='ssh').update(port=6900)
        with self.assertRaisesMessage(ValidationError, 'SSH port'):
            self.provider.validate_deployment()

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
            id='00000000-0000-0000-0000-000000000001', name='idle-provider', hostname='192.0.2.11',
        )
        providers = AppProvider.objects.filter(pk__in=[idle.pk, self.provider.pk])
        with self.assertRaisesMessage(ValidationError, 'current deployment'):
            view.perform_bulk_destroy(providers)
        self.assertEqual(providers.count(), 2)
        deployment.status = 'success'
        deployment.save(update_fields=['status'])
        view.perform_destroy(self.provider)
        self.assertFalse(AppProvider.objects.filter(pk=self.provider.pk).exists())
