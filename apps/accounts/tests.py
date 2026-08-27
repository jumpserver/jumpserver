from datetime import datetime, timedelta, timezone as datetime_timezone
from email.utils import format_datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.db.models import CASCADE
from django.test import SimpleTestCase
from django.urls import resolve
from django.utils import timezone
from httpsig import HeaderSigner
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory
from simple_history.models import HistoricalRecords

from accounts.api.account.credential import CredentialPolicyViewSet
from accounts.const import CredentialPolicyStatus, Source
from accounts.credentials import CredentialError, CredentialPolicyService
from accounts.models import (
    CredentialIssueRequest, CredentialLease, CredentialPolicyVersion,
)
from accounts.models.account import AccountHistoricalRecords
from accounts.serializers.account.account import (
    AccountCreateUpdateSerializerMixin, AccountDetailSerializer,
    AccountSerializer,
)
from accounts.serializers.account.base import BaseAccountSerializer
from accounts.serializers.account.credential import (
    CredentialLeaseRenewSerializer, CredentialLeaseSerializer,
    CredentialPolicySerializer,
)
from accounts.tasks.credential import _credential_execution_is_overdue
from authentication.backends.drf import CredentialServiceAuthentication


class CredentialPolicyDeletionTestCase(SimpleTestCase):
    def test_completed_audit_history_does_not_block_deletion(self):
        policy = MagicMock(status=CredentialPolicyStatus.disabled)
        policy.leases.filter.return_value.exists.return_value = False
        policy.issue_requests.filter.return_value.exists.return_value = False

        CredentialPolicyViewSet().perform_destroy(policy)

        policy.delete.assert_called_once_with()

    def test_audit_history_is_deleted_with_policy(self):
        for model in (
            CredentialPolicyVersion, CredentialIssueRequest, CredentialLease,
        ):
            self.assertIs(
                model._meta.get_field('policy').remote_field.on_delete,
                CASCADE,
            )


class CredentialUsernameTemplateTestCase(SimpleTestCase):
    def test_rejects_unknown_placeholder(self):
        with self.assertRaises(CredentialError) as context:
            CredentialPolicyService.validate_username_template(
                'jms_{asset}_{random}',
            )

        self.assertEqual(
            context.exception.code, 'INVALID_USERNAME_TEMPLATE',
        )

    def test_requires_random_placeholder(self):
        with self.assertRaises(CredentialError) as context:
            CredentialPolicyService.validate_username_template(
                'jms_{application}_{policy}',
            )

        self.assertEqual(
            context.exception.code, 'INVALID_USERNAME_TEMPLATE',
        )

    @patch('accounts.credentials.uuid.uuid4')
    @patch('accounts.credentials.timezone.now')
    def test_renders_supported_placeholders(self, mocked_now, mocked_uuid):
        mocked_now.return_value = datetime(
            2026, 8, 26, 12, 34, 56, tzinfo=datetime_timezone.utc,
        )
        mocked_uuid.return_value.hex = 'abcdef1234567890'
        policy = SimpleNamespace(
            name='Database primary',
            application=SimpleNamespace(name='Payment / API'),
            username_template=(
                'jms_{application}_{policy}_{timestamp}_{random}'
            ),
        )

        username = CredentialPolicyService.render_username(policy)

        self.assertEqual(
            username,
            'jms_Payment_API_Database_primary_20260826123456_abcdef1234567890',
        )

    @patch('accounts.credentials.uuid.uuid4')
    def test_preserves_random_suffix_at_platform_limit(self, mocked_uuid):
        mocked_uuid.return_value.hex = 'abcdef1234567890'
        automation = SimpleNamespace(
            push_account_method='push_account_local_windows',
        )
        policy = SimpleNamespace(
            name='Very long credential policy',
            application=SimpleNamespace(name='Very long application'),
            asset=SimpleNamespace(
                platform=SimpleNamespace(automation=automation),
            ),
            username_template='jms_{application}_{policy}_{random}',
        )

        username = CredentialPolicyService.render_username(policy)

        self.assertEqual(len(username), 20)
        self.assertTrue(username.endswith('_abcdef1234567890'))

    def test_remote_cleanup_uses_issuance_snapshot(self):
        policy = SimpleNamespace(
            asset_id='asset-id',
            platform_params={'account_host': 'new-host'},
            management_account_id='new-management-account',
        )

        with patch.object(
            CredentialPolicyService,
            '_create_execution',
            return_value=SimpleNamespace(id='execution-id'),
        ) as create_execution:
            CredentialPolicyService._prepare_remote_removal(
                policy,
                'temporary-user',
                {'account_host': 'issued-host'},
                'issued-management-account',
            )

        snapshot = create_execution.call_args.args[2]
        self.assertEqual(snapshot['params']['account_host'], 'issued-host')
        self.assertEqual(
            snapshot['management_account'], 'issued-management-account',
        )


class CredentialLeaseHistoryTestCase(SimpleTestCase):
    def test_temporary_account_secret_is_not_historized(self):
        records = AccountHistoricalRecords()
        account = SimpleNamespace(source=Source.CREDENTIAL_LEASE)

        with patch.object(HistoricalRecords, 'post_save') as post_save:
            records.post_save(account, created=True)

        post_save.assert_not_called()

    def test_rejects_client_created_temporary_account_source(self):
        with self.assertRaises(exceptions.ValidationError):
            AccountCreateUpdateSerializerMixin.validate_source(
                Source.CREDENTIAL_LEASE,
            )


class CredentialManagedAccountSerializerTestCase(SimpleTestCase):
    def test_account_detail_exposes_managed_state(self):
        self.assertTrue(
            AccountDetailSerializer().fields[
                'is_credential_managed'
            ].read_only,
        )

    @patch.object(BaseAccountSerializer, 'update')
    def test_regular_account_update_still_clears_source_link(self, update):
        account = SimpleNamespace(is_credential_managed=False)
        update.return_value = account

        AccountSerializer().update(account, {'comment': 'changed'})

        update.assert_called_once_with(
            account, {'comment': 'changed', 'source_id': None},
        )

    @patch.object(BaseAccountSerializer, 'update')
    def test_allows_non_credential_fields_for_static_policy_account(self, update):
        account = SimpleNamespace(
            is_credential_managed=True, source=Source.LOCAL,
        )
        update.return_value = account
        data = {
            'name': 'renamed',
            'privileged': False,
            'is_active': True,
            'comment': 'managed account',
            'labels': [],
        }

        result = AccountSerializer().update(account, data)

        self.assertIs(result, account)
        update.assert_called_once_with(account, data)

    @patch.object(BaseAccountSerializer, 'update')
    def test_rejects_credential_fields_for_static_policy_account(self, update):
        account = SimpleNamespace(
            is_credential_managed=True, source=Source.LOCAL,
        )

        with self.assertRaises(exceptions.ValidationError):
            AccountSerializer().update(account, {'secret': 'new-secret'})

        update.assert_not_called()

    @patch.object(BaseAccountSerializer, 'update')
    def test_rejects_all_changes_for_temporary_account(self, update):
        account = SimpleNamespace(
            is_credential_managed=True, source=Source.CREDENTIAL_LEASE,
        )

        with self.assertRaises(exceptions.ValidationError):
            AccountSerializer().update(account, {'comment': 'changed'})

        update.assert_not_called()


class CredentialVaultDeletionTestCase(SimpleTestCase):
    def test_temporary_account_secrets_are_force_deleted(self):
        historical = SimpleNamespace(delete=MagicMock())
        history_objects = MagicMock()
        history_objects.filter.return_value = [historical]
        account = SimpleNamespace(
            id='account-id',
            history=SimpleNamespace(
                model=SimpleNamespace(objects=history_objects),
            ),
            delete=MagicMock(),
        )

        with patch('accounts.backends.vault_client') as vault:
            CredentialPolicyService._delete_local_account(account)

        vault.delete.assert_has_calls([
            call(historical, force=True),
            call(account, force=True),
        ])
        self.assertTrue(historical.skip_vault_when_deleting)
        self.assertTrue(account.skip_vault_when_deleting)

    def test_aws_force_delete_disables_recovery_window(self):
        from accounts.backends.aws.service import AmazonSecretsManagerClient

        service = AmazonSecretsManagerClient.__new__(
            AmazonSecretsManagerClient,
        )
        service.client = MagicMock()

        service.delete('temporary-secret', force=True)

        service.client.delete_secret.assert_called_once_with(
            SecretId='temporary-secret', ForceDeleteWithoutRecovery=True,
        )

    def test_azure_force_delete_waits_and_purges(self):
        from accounts.backends.azure.service import AZUREVaultClient

        service = AZUREVaultClient.__new__(AZUREVaultClient)
        service.client = MagicMock()

        service.delete('temporary-secret', force=True)

        service.client.begin_delete_secret.return_value.wait.assert_called_once()
        service.client.purge_deleted_secret.assert_called_once_with(
            'temporary-secret',
        )


class CredentialExecutionRecoveryTestCase(SimpleTestCase):
    def test_only_recovers_executions_past_the_grace_period(self):
        self.assertTrue(_credential_execution_is_overdue(
            SimpleNamespace(snapshot={'deadline': 100}), 100,
        ))
        self.assertFalse(_credential_execution_is_overdue(
            SimpleNamespace(snapshot={'deadline': 101}), 100,
        ))
        self.assertFalse(_credential_execution_is_overdue(
            SimpleNamespace(snapshot={'deadline': 'invalid'}), 100,
        ))


class CredentialIssueSecretCleanupTestCase(SimpleTestCase):
    def test_failed_issue_removes_provisional_secret(self):
        issue = SimpleNamespace(
            provisional_secret='temporary-secret',
            save=MagicMock(),
        )

        CredentialPolicyService._fail_issue(
            issue, 'failed', 'TEST_FAILURE', 'test failure',
        )

        self.assertIsNone(issue.provisional_secret)


class CredentialLeaseRenewSerializerTestCase(SimpleTestCase):
    def test_rejects_increment_larger_than_database_integer(self):
        serializer = CredentialLeaseRenewSerializer(data={
            'increment': 10 ** 100,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('increment', serializer.errors)


class CredentialTaskLinkSerializerTestCase(SimpleTestCase):
    def test_policy_operation_task_id_is_read_only(self):
        self.assertTrue(
            CredentialPolicySerializer().fields['operation_task_id'].read_only,
        )

    def test_exposes_only_policy_celery_task_id(self):
        policy = SimpleNamespace(last_execution=SimpleNamespace(
            snapshot={
                'celery_task_id': 'policy-task-id',
                'secret': 'must-not-be-returned',
            },
        ))

        self.assertEqual(
            CredentialPolicySerializer.get_last_task_id(policy),
            'policy-task-id',
        )

    def test_exposes_only_lease_revoke_task_id(self):
        lease = SimpleNamespace(revoke_execution=SimpleNamespace(
            snapshot={
                'celery_task_id': 'revoke-task-id',
                'secret': 'must-not-be-returned',
            },
        ))

        self.assertEqual(
            CredentialLeaseSerializer.get_revoke_task_id(lease),
            'revoke-task-id',
        )
class CredentialServiceAuthenticationTestCase(SimpleTestCase):
    factory = APIRequestFactory()
    signed_headers = (
        '(request-target) date x-jms-org x-source x-jms-nonce'
    )

    def make_request(self, algorithm, date):
        authorization = (
            'Signature keyId="00000000-0000-0000-0000-000000000001",'
            f'algorithm="{algorithm}",headers="{self.signed_headers}",'
            'signature="dGVzdA=="'
        )
        return self.factory.get(
            '/api/v1/accounts/credential-policies/test/credential/',
            HTTP_AUTHORIZATION=authorization,
            HTTP_DATE=format_datetime(date, usegmt=True),
            HTTP_X_JMS_ORG='00000000-0000-0000-0000-000000000002',
            HTTP_X_SOURCE='jms-pam',
            HTTP_X_JMS_NONCE='0000000000000001',
        )

    def test_rejects_expired_date_before_database_lookup(self):
        request = self.make_request(
            'hmac-sha256', timezone.now() - timedelta(minutes=6),
        )

        with self.assertRaises(exceptions.AuthenticationFailed):
            CredentialServiceAuthentication().authenticate(request)

    def test_rejects_weak_algorithm_before_database_lookup(self):
        request = self.make_request('hmac-sha1', timezone.now())

        with self.assertRaises(exceptions.AuthenticationFailed):
            CredentialServiceAuthentication().authenticate(request)

    @patch('authentication.backends.drf.cache.add', return_value=True)
    def test_accepts_valid_credential_service_signature(self, cache_add):
        path = '/api/v1/accounts/credential-service/policies/test/credential/'
        headers = {
            'Date': format_datetime(timezone.now(), usegmt=True),
            'X-JMS-ORG': 'org-id',
            'X-Source': 'jms-pam',
            'X-JMS-Nonce': '0000000000000002',
        }
        signer = HeaderSigner(
            'app-id', 'app-secret', algorithm='hmac-sha256',
            headers=self.signed_headers.split(),
        )
        signed = signer.sign(headers, method='get', path=path)
        request = self.factory.get(
            path,
            HTTP_AUTHORIZATION=signed['authorization'],
            HTTP_DATE=signed['date'],
            HTTP_X_JMS_ORG=signed['x-jms-org'],
            HTTP_X_SOURCE=signed['x-source'],
            HTTP_X_JMS_NONCE=signed['x-jms-nonce'],
        )
        application = SimpleNamespace(
            id='app-id', secret='app-secret', org_id='org-id',
        )
        authenticator = CredentialServiceAuthentication()

        with patch.object(
            authenticator, 'get_object', return_value=application,
        ), patch.object(
            authenticator, 'is_ip_allow', return_value=True,
        ), patch.object(
            authenticator, 'after_authenticate_update_date',
        ):
            user, key_id = authenticator.authenticate(request)

        self.assertIs(user, application)
        self.assertEqual(key_id, 'app-id')
        cache_add.assert_called_once()

    def test_rejects_malformed_application_id(self):
        request = self.make_request('hmac-sha256', timezone.now())
        request.META['HTTP_AUTHORIZATION'] = request.META[
            'HTTP_AUTHORIZATION'
        ].replace(
            '00000000-0000-0000-0000-000000000001', 'not-a-uuid',
        )

        with self.assertRaises(exceptions.AuthenticationFailed):
            CredentialServiceAuthentication().authenticate(request)

    def test_requires_signed_digest_for_request_body(self):
        authorization = (
            'Signature keyId="00000000-0000-0000-0000-000000000001",'
            f'algorithm="hmac-sha256",headers="{self.signed_headers}",'
            'signature="dGVzdA=="'
        )
        request = self.factory.post(
            '/api/v1/accounts/credential-service/leases/test/renew/',
            {'increment': 300}, format='json',
            HTTP_AUTHORIZATION=authorization,
            HTTP_DATE=format_datetime(timezone.now(), usegmt=True),
            HTTP_X_JMS_ORG='00000000-0000-0000-0000-000000000002',
            HTTP_X_SOURCE='jms-pam',
            HTTP_X_JMS_NONCE='0000000000000003',
        )

        with self.assertRaises(exceptions.AuthenticationFailed):
            CredentialServiceAuthentication().authenticate(request)

    @patch('authentication.backends.drf.cache.add', side_effect=[True, False])
    def test_rejects_replayed_request(self, cache_add):
        path = '/api/v1/accounts/credential-service/policies/test/credentials/'
        headers = {
            'Date': format_datetime(timezone.now(), usegmt=True),
            'X-JMS-ORG': 'org-id',
            'X-Source': 'jms-pam',
            'X-JMS-Nonce': '0000000000000004',
        }
        signer = HeaderSigner(
            'app-id', 'app-secret', algorithm='hmac-sha256',
            headers=self.signed_headers.split(),
        )
        signed = signer.sign(headers, method='post', path=path)
        request = self.factory.generic(
            'POST', path, b'', content_type='application/json',
            HTTP_AUTHORIZATION=signed['authorization'],
            HTTP_DATE=signed['date'],
            HTTP_X_JMS_ORG=signed['x-jms-org'],
            HTTP_X_SOURCE=signed['x-source'],
            HTTP_X_JMS_NONCE=signed['x-jms-nonce'],
        )
        application = SimpleNamespace(
            id='app-id', secret='app-secret', org_id='org-id',
        )
        authenticator = CredentialServiceAuthentication()

        with patch.object(
            authenticator, 'get_object', return_value=application,
        ), patch.object(
            authenticator, 'is_ip_allow', return_value=True,
        ), patch.object(
            authenticator, 'after_authenticate_update_date',
        ):
            authenticator.authenticate(request)
            with self.assertRaises(exceptions.AuthenticationFailed):
                authenticator.authenticate(request)

        self.assertEqual(cache_add.call_count, 2)
        self.assertEqual(cache_add.call_args_list[0].kwargs['timeout'], 600)


class CredentialServiceIssueTransactionTestCase(SimpleTestCase):
    def test_issue_endpoint_commits_before_dispatching_worker(self):
        match = resolve(
            '/api/v1/accounts/credential-service/policies/'
            '00000000-0000-0000-0000-000000000001/credentials/'
        )

        self.assertEqual(match.func._non_atomic_requests, {'default'})
