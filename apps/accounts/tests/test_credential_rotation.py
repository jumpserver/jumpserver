import shlex
from unittest.mock import Mock

import requests
from django.core import signing
from django.db.models import F
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.credential import (
    CredentialClientInstanceViewSet, CredentialClientViewSet,
    CredentialPolicyViewSet,
)
from accounts.const import ChangeSecretRecordStatusChoice
from accounts.models import (
    Account, ChangeSecretRecord, CredentialPolicy, IntegrationApplication,
)
from assets.const import Category
from assets.models import Asset, Platform
from orgs.models import Organization
from orgs.utils import set_current_org
from users.models import User

from accounts.demos.python.jms_pam.main import HTTPSignatureAuth, SignedClient


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
        self.policy = CredentialPolicy.objects.create(
            name='PostgreSQL primary',
            primary_account=self.primary,
            backup_account=self.backup,
            published_account=self.primary,
        )

    def request(self, method, path, data=None, user=None):
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
            data={'key': self.policy.key, 'instance_id': instance_id},
            user=application,
        )
        fetched = view(request)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.data['account']['id'], str(account.id))

        view = CredentialClientViewSet.as_view({'post': 'confirm'})
        request = self.request(
            'post', '/api/v1/accounts/credential-client/confirm/',
            data={
                'key': self.policy.key,
                'instance_id': instance_id,
                'revision': fetched.data['revision'],
                'account_id': fetched.data['account']['id'],
            },
            user=application,
        )
        confirmed = view(request)
        self.assertEqual(confirmed.status_code, 200)

    def policy_action(self, action):
        view = CredentialPolicyViewSet.as_view({'post': action})
        request = self.request(
            'post',
            f'/api/v1/accounts/credential-policies/{self.policy.id}/{action}/',
        )
        return view(request, pk=self.policy.id)

    def fetch_and_confirm(self, account):
        response = self.client_action(
            'credential', method='get',
            data={'key': self.policy.key, 'instance_id': 'order-node-1'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['account']['id'], str(account.id))
        response = self.client_action('confirm', data={
            'key': self.policy.key,
            'instance_id': 'order-node-1',
            'revision': response.data['revision'],
            'account_id': response.data['account']['id'],
        })
        self.assertEqual(response.status_code, 200)

    def test_primary_backup_primary_rotation(self):
        self.fetch_and_confirm(self.primary)

        response = self.policy_action('start_rotation')
        self.assertEqual(response.status_code, 200)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, CredentialPolicy.Status.waiting_backup)
        self.assertEqual(self.policy.published_account_id, self.backup.id)

        blocked = self.policy_action('check_usage')
        self.assertEqual(blocked.status_code, 409)

        self.fetch_and_confirm(self.backup)
        ready = self.policy_action('check_usage')
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(
            ready.data['status']['value'], CredentialPolicy.Status.ready_for_change
        )

        original_version = self.policy.primary_version_at_start
        Account.objects.filter(id=self.primary.id).update(
            version=F('version') + 1,
            change_secret_status=ChangeSecretRecordStatusChoice.success,
        )
        ChangeSecretRecord.objects.create(
            account=self.primary,
            asset=self.asset,
            account_version=original_version,
            status=ChangeSecretRecordStatusChoice.success,
            date_finished=timezone.now(),
        )
        switched_back = self.policy_action('check_secret_change')
        self.assertEqual(switched_back.status_code, 200)
        self.assertEqual(
            str(switched_back.data['published_account']['id']),
            str(self.primary.id),
        )

        self.fetch_and_confirm(self.primary)
        completed = self.policy_action('complete_rotation')
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.data['status']['value'], CredentialPolicy.Status.idle)
        self.assertIsNotNone(completed.data['date_last_rotated'])

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
        self.assertEqual(self.policy_action('start_rotation').status_code, 200)

        self.policy.refresh_from_db()
        self.fetch_and_confirm_for(
            self.application, 'order-node-1', self.backup
        )
        blocked = self.policy_action('check_usage')
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(
            blocked.data['blockers'][0]['application']['name'],
            report_application.name,
        )

        self.fetch_and_confirm_for(
            report_application, 'report-node-1', self.backup
        )
        self.assertEqual(self.policy_action('check_usage').status_code, 200)

    def test_agent_registration_token_can_only_be_used_once(self):
        self.application.credential_access_mode = IntegrationApplication.AccessMode.agent
        self.application.save(update_fields=['credential_access_mode'])
        token = signing.dumps({
            'application_id': str(self.application.id),
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
        self.application.credential_access_mode = IntegrationApplication.AccessMode.agent
        self.application.save(update_fields=['credential_access_mode'])
        app_user = 'service; touch /tmp/should-not-run'
        view = IntegrationApplicationViewSet.as_view({'post': 'agent_registration'})
        request = self.request(
            'post',
            f'/api/v1/accounts/integration-applications/{self.application.id}/agent-registration/',
            data={
                'credential_keys': [self.policy.key],
                'instance_id': 'order-agent-1',
                'app_user': app_user,
            },
        )
        response = view(request, pk=self.application.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'--app-user {shlex.quote(app_user)}', response.data['install_command'])


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
