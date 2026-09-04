import shlex
import threading
import json
from datetime import timedelta
from unittest.mock import Mock, patch, mock_open

import requests
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.credential_client.manager import ClientAccessConfigurationManager, CredentialClientManager
from accounts.credential_rotation import CredentialRotationManager
from accounts.serializers import ApplicationCredentialSerializer, ClientAccessConfigurationSerializer
from accounts.api.account.credential import (
    CredentialClientInstanceViewSet, CredentialClientViewSet,
    ApplicationCredentialViewSet, ClientAccessConfigurationViewSet,
    CredentialRotationRecordViewSet,
)
from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.const import ChangeSecretRecordStatusChoice
from accounts.demos.python.jms_pam.agent import Agent
from accounts.demos.python.jms_pam.main import (
    CLIENT_PATH, CredentialAPIClient, HTTPSignatureAuth, SignedClient, JumpServerPAMClient,
)
from accounts.models import (
    Account, AutomationExecution, ChangeSecretRecord, ApplicationCredential, IntegrationApplication,
    ClientAccessConfiguration,
    CredentialClientInstance,
)
from assets.const import Category
from assets.models import Asset, Platform
from authentication.backends.drf import (
    CredentialAgentAuthentication, ServiceAuthentication,
)
from orgs.models import Organization
from orgs.utils import set_current_org
from users.models import User


class CredentialRotationTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.org = Organization.default()
        set_current_org(self.org)
        self.admin = User.objects.create_superuser(
            username='credential-admin', password='password',
            name='Credential admin', email='credential-admin@example.com',
        )
        self.platform = Platform.objects.create(
            name='CredentialTestPostgreSQL',
            category=Category.DATABASE,
            type='postgresql',
        )
        self.asset = Asset.objects.create(
            name='credential-test-pg', address='127.0.0.1',
            platform=self.platform,
        )
        self.primary = Account.objects.create(
            name='account-a', username='account-a', asset=self.asset,
            secret='primary-secret',
        )
        self.backup = Account.objects.create(
            name='account-b', username='account-b', asset=self.asset,
            secret='backup-secret',
        )
        self.application = IntegrationApplication.objects.create(
            name='order-service', secret='application-secret',
            accounts={
                'type': 'ids',
                'ids': [str(self.primary.id), str(self.backup.id)],
            },
        )
        self.credential = ApplicationCredential.objects.create(
            name='PostgreSQL primary',
            primary_account=self.primary,
            backup_account=self.backup,
            published_account=self.primary,
        )

    def request(self, method, path, data=None, user=None):
        if isinstance(user, IntegrationApplication):
            configuration, _ = ClientAccessConfiguration.objects.get_or_create(
                application=user, name='Test SDK', defaults={'type': 'sdk'},
            )
            configuration.credentials.add(self.credential)
            data = dict(data or {}, configuration_id=str(configuration.id))
        creator = getattr(self.factory, method)
        request = creator(
            path, data=data or {}, format='json',
            HTTP_X_JMS_ORG=str(self.org.id),
        )
        force_authenticate(request, user=user or self.admin)
        return request

    def client_action(self, action, method='post', data=None):
        view = CredentialClientViewSet.as_view({method: action})
        request = self.request(
            method,
            f'/api/v1/accounts/credential-client/{action}/',
            data=data,
            user=self.application,
        )
        return view(request)

    def fetch_and_confirm_for(self, application, instance_id, account):
        view = CredentialClientViewSet.as_view({'get': 'credential'})
        request = self.request(
            'get', '/api/v1/accounts/credential-client/credential/',
            data={'key': self.credential.key, 'instance_id': instance_id},
            user=application,
        )
        fetched = view(request)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.data['account']['id'], str(account.id))

        view = CredentialClientViewSet.as_view({'post': 'confirm'})
        request = self.request(
            'post', '/api/v1/accounts/credential-client/confirm/',
            data={
                'key': self.credential.key,
                'instance_id': instance_id,
                'revision': fetched.data['revision'],
                'account_id': fetched.data['account']['id'],
            },
            user=application,
        )
        confirmed = view(request)
        self.assertEqual(confirmed.status_code, 200)

    def credential_action(self, action):
        view = ApplicationCredentialViewSet.as_view({'post': action})
        request = self.request(
            'post',
            f'/api/v1/accounts/application-credentials/{self.credential.id}/{action}/',
        )
        return view(request, pk=self.credential.id)

    def fetch_and_confirm(self, account):
        response = self.client_action(
            'credential', method='get',
            data={'key': self.credential.key, 'instance_id': 'order-node-1'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['account']['id'], str(account.id))
        response = self.client_action('confirm', data={
            'key': self.credential.key,
            'instance_id': 'order-node-1',
            'revision': response.data['revision'],
            'account_id': response.data['account']['id'],
        })
        self.assertEqual(response.status_code, 200)

    def test_primary_backup_primary_rotation(self):
        self.fetch_and_confirm(self.primary)

        response = self.credential_action('start_rotation')
        self.assertEqual(response.status_code, 200)
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, ApplicationCredential.Status.waiting_backup)
        self.assertEqual(self.credential.published_account_id, self.backup.id)

        blocked = self.credential_action('check_usage')
        self.assertEqual(blocked.status_code, 409)

        self.fetch_and_confirm(self.backup)
        ready = self.credential_action('check_usage')
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(
            ready.data['status']['value'], ApplicationCredential.Status.ready_for_change
        )

        original_version = self.credential.primary_version_at_start
        execution_count = AutomationExecution.objects.count()
        changed = self.credential_action('change_secret')
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(AutomationExecution.objects.count(), execution_count)
        self.credential.refresh_from_db()
        self.assertIsNone(self.credential.change_execution_id)
        execution = AutomationExecution.objects.create(type='change_secret')
        Account.objects.filter(id=self.primary.id).update(
            version=F('version') + 1,
            change_secret_status=ChangeSecretRecordStatusChoice.success,
        )
        ChangeSecretRecord.objects.create(
            execution=execution,
            account=self.primary,
            asset=self.asset,
            account_version=original_version,
            status=ChangeSecretRecordStatusChoice.success,
            date_finished=timezone.now(),
        )
        switched_back = self.credential_action('check_secret_change')
        self.assertEqual(switched_back.status_code, 200)
        self.assertEqual(
            str(switched_back.data['published_account']['id']),
            str(self.primary.id),
        )

        self.fetch_and_confirm(self.primary)
        completed = self.credential_action('complete_rotation')
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data['status']['value'], ApplicationCredential.Status.idle)
        self.assertIsNotNone(completed.data['date_last_rotated'])

    def test_rotation_record_search_keeps_credential_scope(self):
        matched = self.credential.rotation_records.create(
            created_by='alice', comment='manual database change',
        )
        self.credential.rotation_records.create(created_by='bob', comment='other change')
        other = ApplicationCredential.objects.create(
            name='Other credential', primary_account=self.backup,
            published_account=self.backup, type='fixed', rotation_mode='',
        )
        other.rotation_records.create(created_by='alice', comment='manual database change')
        view = CredentialRotationRecordViewSet.as_view({'get': 'list'})
        for search in ['alice', 'database', 'not-found']:
            response = view(self.request('get', '/api/v1/accounts/credential-rotation-records/', {
                'credential': str(self.credential.id), 'search': search,
            }))
            self.assertEqual(response.status_code, 200)
            rows = response.data['results'] if isinstance(response.data, dict) else response.data
            self.assertEqual(
                [str(row['id']) for row in rows],
                [] if search == 'not-found' else [str(matched.id)],
            )

    def test_every_application_must_release_primary_account(self):
        report_application = IntegrationApplication.objects.create(
            name='report-service', secret='report-secret',
            accounts={
                'type': 'ids',
                'ids': [str(self.primary.id), str(self.backup.id)],
            },
        )
        self.fetch_and_confirm_for(
            self.application, 'order-node-1', self.primary
        )
        self.fetch_and_confirm_for(
            report_application, 'report-node-1', self.primary
        )
        self.assertEqual(self.credential_action('start_rotation').status_code, 200)

        self.credential.refresh_from_db()
        self.fetch_and_confirm_for(
            self.application, 'order-node-1', self.backup
        )
        blocked = self.credential_action('check_usage')
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(
            blocked.data['blockers'][0]['application']['name'],
            report_application.name,
        )

        self.fetch_and_confirm_for(
            report_application, 'report-node-1', self.backup
        )
        self.assertEqual(self.credential_action('check_usage').status_code, 200)

    def test_rotation_can_be_cancelled_before_primary_secret_changes(self):
        self.fetch_and_confirm(self.primary)
        self.assertEqual(self.credential_action('start_rotation').status_code, 200)

        cancelled = self.credential_action('cancel_rotation')
        self.assertEqual(cancelled.status_code, 200)
        self.assertTrue(cancelled.data['rotation_cancelled'])
        self.assertEqual(
            str(cancelled.data['published_account']['id']),
            str(self.primary.id),
        )

        self.fetch_and_confirm(self.primary)
        completed = self.credential_action('complete_rotation')
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(
            completed.data['status']['value'], ApplicationCredential.Status.idle
        )
        self.assertIsNone(completed.data['date_last_rotated'])

    def test_agent_registration_token_can_only_be_used_once(self):
        configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Test Agent', type='agent', app_user='app',
        )
        configuration.credentials.add(self.credential)
        token = signing.dumps({
            'application_id': str(self.application.id),
            'configuration_id': str(configuration.id),
            'org_id': str(self.org.id),
            'nonce': str(self.application.id),
        }, salt='credential-agent-register')
        view = CredentialClientViewSet.as_view(
            {'post': 'register_agent'},
            authentication_classes=[],
            permission_classes=[AllowAny],
        )
        data = {
            'token': token,
            'instance_id': 'order-agent-1',
            'name': 'Order agent',
        }
        first = view(self.factory.post(
            '/api/v1/accounts/credential-client/register-agent/',
            data=data, format='json',
        ))
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.data['agent_secret'])

        second = view(self.factory.post(
            '/api/v1/accounts/credential-client/register-agent/',
            data=data, format='json',
        ))
        self.assertEqual(second.status_code, 400)

    def test_agent_install_command_quotes_user_input(self):
        app_user = 'service; touch /tmp/should-not-run'
        configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Test Agent', type='agent', app_user=app_user,
        )
        configuration.credentials.add(self.credential)
        data = ClientAccessConfigurationManager(configuration).materials('http://testserver')
        self.assertIn(f'--app-user {shlex.quote(app_user)}', data['install_command'])
        self.assertIn(
            'pip install --index-url https://pypi.org/simple http://testserver/api/v1/accounts/python-sdk/',
            data['install_command'],
        )
        self.assertNotIn('--find-links', data['install_command'])

    def create_configuration(self, kind='sdk'):
        configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name=f'Configured {kind}', type=kind, app_user='app',
        )
        configuration.credentials.add(self.credential)
        return configuration

    def test_fixed_account_uses_actual_account_version_and_does_not_rotate(self):
        self.credential.type = 'fixed'
        self.credential.rotation_mode = ''
        self.credential.backup_account = None
        self.credential.save()
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save()
        configuration = self.create_configuration()
        manager = CredentialClientManager(self.application, configuration.id, 'fixed-client')
        first = manager.fetch(self.credential.key, '127.0.0.1')
        self.assertEqual(first['account']['secret'], self.primary.secret)
        Account.objects.filter(id=self.primary.id).update(version=F('version') + 1)
        second = manager.fetch(self.credential.key, '127.0.0.1')
        self.assertEqual(second['revision'], first['revision'] + 1)
        manager.confirm(self.credential.key, second['revision'], self.primary.id)
        with self.assertRaises(ValidationError):
            CredentialRotationManager(self.credential.id).start()

    def test_configuration_selection_and_account_authorization_both_required(self):
        configuration = self.create_configuration()
        manager = CredentialClientManager(self.application, configuration.id, 'client')
        configuration.credentials.clear()
        with self.assertRaises(PermissionDenied):
            manager.fetch(self.credential.key, '127.0.0.1')
        configuration.credentials.add(self.credential)
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save()
        with self.assertRaises(PermissionDenied):
            manager.fetch(self.credential.key, '127.0.0.1')

    def test_disabled_instance_is_excluded_and_cannot_fetch(self):
        self.fetch_and_confirm(self.primary)
        self.credential_action('start_rotation')
        self.credential.refresh_from_db()
        self.assertTrue(self.credential.get_blockers())
        client = self.application.credential_clients.get(instance_id='order-node-1')
        client.is_active = False
        client.save()
        self.assertEqual(self.credential.get_blockers(), [])
        self.assertEqual(self.credential_action('check_usage').status_code, 200)
        with self.assertRaises(PermissionDenied):
            CredentialClientManager(self.application, client.configuration_id, client.instance_id)

    def test_sdk_and_agent_can_use_the_same_application(self):
        sdk_config = self.create_configuration()
        agent_config = self.create_configuration('agent')
        agent = CredentialClientInstance.objects.create(
            configuration=agent_config, application=self.application,
            type='agent', instance_id='agent', secret='agent-secret',
        )
        sdk = CredentialClientManager(self.application, sdk_config.id, 'sdk')
        agent_manager = CredentialClientManager(agent)
        self.assertEqual(sdk.fetch(self.credential.key, '127.0.0.1')['key'], self.credential.key)
        self.assertEqual(agent_manager.fetch(self.credential.key, '127.0.0.1')['key'], self.credential.key)
        CredentialRotationManager(self.credential.id).start()
        self.credential.refresh_from_db()
        self.assertEqual(len(self.credential.get_blockers()), 2)

    def test_single_account_waits_for_verified_task_and_client_confirmation(self):
        self.credential.rotation_mode = 'single'
        self.credential.backup_account = None
        self.credential.save()
        self.fetch_and_confirm(self.primary)
        manager = CredentialRotationManager(self.credential.id)
        self.assertEqual(manager.start().status, 'ready_for_change')
        execution_count = AutomationExecution.objects.count()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            changed = manager.change_secret()
        self.assertEqual(callbacks, [])
        self.assertEqual(AutomationExecution.objects.count(), execution_count)
        self.assertEqual(changed.status, 'changing_secret')
        self.assertIsNone(changed.change_execution_id)
        with self.assertRaises(ValidationError):
            manager.change_secret()
        with self.assertRaises(ValidationError):
            manager.check_secret_change()
        configuration = self.application.access_configurations.get(name='Test SDK')
        sdk = CredentialClientManager(self.application, configuration.id, 'order-node-1')
        with self.assertRaisesMessage(ValidationError, 'The account secret is changing.'):
            sdk.fetch(self.credential.key, '127.0.0.1')
        execution = AutomationExecution.objects.create(type='change_secret')
        ChangeSecretRecord.objects.create(
            account=self.primary, asset=self.asset,
            execution=execution,
            account_version=changed.primary_version_at_start,
            status='success', verification_status='success', date_finished=timezone.now(),
        )
        Account.objects.filter(id=self.primary.id).update(
            version=F('version') + 1, change_secret_status='success',
        )
        checked = manager.check_secret_change()
        self.assertEqual(checked.status, 'waiting_primary')
        self.assertEqual(checked.change_execution_id, execution.id)
        self.assertTrue(manager.complete()[1])
        self.fetch_and_confirm(self.primary)
        self.assertEqual(manager.complete()[0].status, 'idle')
        self.assertEqual(self.credential.rotation_records.get().status, 'success')

    def test_manual_secret_change_requires_current_successful_account_record(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        manager.check_usage()
        changed = manager.change_secret()
        execution = AutomationExecution.objects.create(type='change_secret')
        Account.objects.filter(id=self.primary.id).update(
            version=F('version') + 2, change_secret_status='success',
        )
        record = ChangeSecretRecord.objects.create(
            account=self.primary, asset=self.asset, execution=execution,
            account_version=changed.primary_version_at_start + 1,
            status='success', date_finished=timezone.now(),
        )
        valid = {
            'account_id': self.primary.id,
            'account_version': changed.primary_version_at_start + 1,
            'status': 'success',
            'date_finished': record.date_finished,
        }
        for invalid in [
            {'account_id': self.backup.id},
            {'account_version': changed.primary_version_at_start},
            {'status': 'failed'},
            {'status': 'unverified'},
            {'date_finished': changed.date_rotation_started - timedelta(seconds=1)},
        ]:
            with self.subTest(invalid=invalid):
                ChangeSecretRecord.objects.filter(id=record.id).update(**(valid | invalid))
                with self.assertRaises(ValidationError):
                    manager.check_secret_change()
        ChangeSecretRecord.objects.filter(id=record.id).update(**valid)
        checked = manager.check_secret_change()
        self.assertEqual(checked.status, 'waiting_primary')
        self.assertEqual(checked.change_execution_id, execution.id)

    def test_serializer_normalizes_fixed_accounts_and_checks_configuration_authorization(self):
        serializer = ApplicationCredentialSerializer(self.credential, data={
            'type': 'fixed', 'backup_account': str(self.backup.id),
        }, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        credential = serializer.save()
        self.assertIsNone(credential.backup_account)
        self.assertEqual(credential.rotation_mode, '')
        self.application.accounts = {'type': 'ids', 'ids': [str(self.backup.id)]}
        self.application.save()
        serializer = ClientAccessConfigurationSerializer(data={
            'name': 'Invalid config', 'type': 'sdk',
            'application': str(self.application.id), 'credentials': [str(credential.id)],
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('credentials', serializer.errors)

    def test_configuration_crud_and_paginated_list_fields(self):
        view = ClientAccessConfigurationViewSet.as_view({'post': 'create'})
        response = view(self.request('post', '/api/v1/accounts/client-access-configurations/', data={
            'name': 'Saved SDK', 'type': 'sdk', 'application': str(self.application.id),
            'credentials': [str(self.credential.id)],
        }))
        self.assertEqual(response.status_code, 201, response.data)
        configuration = ClientAccessConfiguration.objects.get(id=response.data['id'])
        self.assertEqual(list(configuration.credentials.all()), [self.credential])
        self.assertTrue(self.credential.applications.filter(id=self.application.id).exists())
        view = ClientAccessConfigurationViewSet.as_view({'get': 'list'})
        response = view(self.request('get', '/api/v1/accounts/client-access-configurations/', data={'limit': 10}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('instances_amount', response.data['results'][0])
        self.assertNotIn(self.application.secret, json.dumps(response.data, default=str))
        self.fetch_and_confirm(self.primary)
        view = ApplicationCredentialViewSet.as_view({'get': 'list'})
        response = view(self.request('get', '/api/v1/accounts/application-credentials/', data={
            'limit': 10, 'fields_size': 'small',
        }))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data['results'][0]['last_fetched'])
        self.assertEqual(response.data['results'][0]['applications_amount'], 1)

    def test_materials_require_permission_and_user_confirmation(self):
        configuration = self.create_configuration()
        view = ClientAccessConfigurationViewSet.as_view(
            {'post': 'materials'}, **ClientAccessConfigurationViewSet.materials.kwargs
        )
        path = f'/api/v1/accounts/client-access-configurations/{configuration.id}/materials/'
        with override_settings(SECURITY_VIEW_AUTH_NEED_MFA=True), transaction.atomic():
            response = view(self.request('post', path), pk=configuration.id)
        self.assertEqual(response.status_code, 412)
        with override_settings(SECURITY_VIEW_AUTH_NEED_MFA=False):
            response = view(self.request('post', path), pk=configuration.id)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['config']['app_secret'], self.application.secret)
            self.assertEqual(
                response.data['install_command'],
                'python3 -m pip install --index-url https://pypi.org/simple '
                'http://testserver/api/v1/accounts/python-sdk/',
            )
            self.assertEqual(response['Cache-Control'], 'no-store')
            ordinary_user = User.objects.create_user(username='credential-reader', password='password')
            response = view(self.request('post', path, user=ordinary_user), pk=configuration.id)
            self.assertEqual(response.status_code, 403)

    @override_settings(SECURITY_DISABLE_VIEW_SECRET=False)
    def test_deprecated_endpoint_still_retrieves_one_authorized_account(self):
        view = IntegrationApplicationViewSet.as_view({'get': 'get_account_secret'})
        request = self.factory.get(
            '/api/v1/accounts/integration-applications/account-secret/',
            {'account_id': str(self.primary.id)}, HTTP_X_JMS_ORG=str(self.org.id),
        )
        force_authenticate(request, user=self.application)
        response = view(request)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['secret'], self.primary.secret)
        self.assertEqual(response['X-API-Deprecated'], 'true')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_generated_python_configuration_loads_and_signed_sdk_fetch_authenticates(self):
        configuration = self.create_configuration()
        materials = ClientAccessConfigurationManager(configuration).materials('http://testserver')
        with patch('builtins.open', mock_open(read_data=json.dumps(materials['config']))):
            sdk = JumpServerPAMClient.from_config('jms-pam.json')
        self.assertEqual(sdk.http.configuration_id, str(configuration.id))
        prepared = requests.Request(
            'GET', f'http://testserver{CLIENT_PATH}/credential/',
            params={'key': self.credential.key, 'configuration_id': str(configuration.id), 'instance_id': 'signed-sdk'},
            headers={'Accept': 'application/json', 'Date': 'Fri, 04 Sep 2026 00:00:00 GMT', 'X-JMS-ORG': str(self.org.id), 'X-Source': 'jms-pam'},
            auth=HTTPSignatureAuth(str(self.application.id), self.application.secret),
        ).prepare()
        headers = {f'HTTP_{key.upper().replace("-", "_")}': value for key, value in prepared.headers.items()}
        request = self.factory.get(prepared.path_url, **headers)
        view = CredentialClientViewSet.as_view({'get': 'credential'})
        with patch('authentication.backends.drf.update_service_integration_last_used.delay'):
            response = view(request)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['account']['secret'], self.primary.secret)
        sdk.close()


class CredentialClientInstanceDeletionTestCase(SimpleTestCase):
    def test_only_offline_client_can_be_deleted(self):
        view = CredentialClientInstanceViewSet()
        online_client = Mock(online=True)
        offline_client = Mock(online=False)

        with self.assertRaisesMessage(ValidationError, 'An online client cannot be deleted.'):
            view.perform_destroy(online_client)
        online_client.delete.assert_not_called()

        view.perform_destroy(offline_client)
        offline_client.delete.assert_called_once_with()


class PythonSDKTestCase(SimpleTestCase):
    def test_http_signature(self):
        request = requests.Request(
            'GET',
            'https://jms.example.com/api/v1/accounts/credential-client/credential/?key=cred',
            headers={
                'Accept': 'application/json',
                'Date': 'Tue, 01 Sep 2026 00:00:00 GMT',
                'X-JMS-ORG': 'org',
            },
            auth=HTTPSignatureAuth('app-id', 'secret'),
        ).prepare()

        self.assertEqual(
            request.headers['Authorization'],
            'Signature keyId="app-id",algorithm="hmac-sha256",'
            'signature="UwK5G5SglCFNavwsGqEJM/GsvT9euZMlDDirt8kh6m8=",'
            'headers="(request-target) accept date x-jms-org"',
        )

    def test_http_error_includes_server_detail(self):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError('403 Client Error')
        response.json.return_value = {
            'detail': 'The application does not use SDK access mode.',
        }
        client = SignedClient('https://jms.example.com', 'app-id', 'secret')
        client.session.request = Mock(return_value=response)

        with self.assertRaisesRegex(
            requests.HTTPError,
            '403 Client Error: The application does not use SDK access mode.',
        ):
            client.request('GET', '/credential/')

    def test_sdk_and_agent_share_credential_protocol_client(self):
        sdk = CredentialAPIClient(
            'https://jms.example.com', 'app-id', 'secret',
            instance_id='sdk-instance',
        )
        sdk.request = Mock(return_value={})
        sdk.get_credential('database')
        sdk.confirm({'key': 'database', 'revision': 1, 'account_id': 'account'})
        sdk.heartbeat([])

        sdk.request.assert_any_call(
            'GET', f'{CLIENT_PATH}/credential/',
            params={'key': 'database', 'instance_id': 'sdk-instance'},
        )
        sdk.request.assert_any_call(
            'POST', f'{CLIENT_PATH}/confirm/',
            data={
                'key': 'database', 'revision': 1, 'account_id': 'account',
                'instance_id': 'sdk-instance',
            },
        )
        sdk.request.assert_any_call(
            'POST', f'{CLIENT_PATH}/heartbeat/',
            data={'credentials': [], 'instance_id': 'sdk-instance'},
        )

        agent = CredentialAPIClient(
            'https://jms.example.com', 'agent-id', 'secret',
            source='jms-pam-agent',
        )
        agent.request = Mock(return_value={})
        agent.get_credential('database')
        agent.request.assert_called_once_with(
            'GET', f'{CLIENT_PATH}/credential/', params={'key': 'database'}
        )

    def test_agent_keeps_previous_credentials_when_write_fails(self):
        agent = Agent.__new__(Agent)
        agent.config = {'credential_keys': ['database']}
        agent.remote = Mock()
        agent.remote.get_credential.return_value = {
            'revision': 2,
            'asset': {'id': 'asset', 'name': 'db', 'address': '127.0.0.1'},
            'account': {
                'id': 'account', 'name': 'db-user', 'username': 'db-user',
                'secret_type': 'password', 'secret': 'new-secret',
            },
        }
        agent.credentials = {'database': {'revision': 1, 'secret': 'old-secret'}}
        agent.lock = threading.Lock()

        with patch(
            'accounts.demos.python.jms_pam.agent.atomic_write_json',
            side_effect=OSError('disk full'),
        ), self.assertRaisesRegex(OSError, 'disk full'):
            agent.poll()

        self.assertEqual(agent.credentials['database']['revision'], 1)
        self.assertEqual(agent.credentials['database']['secret'], 'old-secret')

    def test_agent_authentication_reuses_service_authentication(self):
        self.assertTrue(issubclass(
            CredentialAgentAuthentication, ServiceAuthentication
        ))
