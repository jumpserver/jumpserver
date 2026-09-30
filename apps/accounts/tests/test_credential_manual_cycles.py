from uuid import uuid4

from django.db import transaction
from unittest.mock import AsyncMock, patch

from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.const import AuditEvent
from accounts.credential_rotation.cycles import cycle_detail, cycle_directory
from accounts.credential_rotation.events import receive
from accounts.credential_rotation.manual_cycles import start
from accounts.credential_rotation.manager import CredentialRotationManager
from accounts.models import (
    ApplicationAudit, ApplicationCredential, AutomationExecution, ChangeSecretRecord,
    CredentialApplicationBinding, CredentialClientInstance, CredentialRotationEvent, IntegrationApplication,
)
from accounts.tests.base import CredentialTestCase
from common.exceptions import JMSException


class CredentialManualCycleTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.client = CredentialClientInstance.objects.create(
            application=self.application,
            instance_id='manual-cycle-sdk', type='sdk', event_receipts_supported=True,
        )
        CredentialRotationEvent.objects.all().delete()

    def subscription(self):
        self.credential.mode = 'subscription'
        self.credential.save(update_fields=['mode'])
        self.credential.subscription_accounts.add(self.primary, self.backup)

    def test_subscription_cycle_republishes_current_versions_without_secret_changes(self):
        self.subscription()
        _, cycle_id = start(self.credential.id, self.admin.name, self.admin.id)
        detail = cycle_detail(self.credential, cycle_id)
        self.assertEqual(detail['kind'], 'subscription_refresh')
        self.assertEqual(detail['status'], 'published')
        self.assertEqual(detail['event_count'], 2)
        self.assertEqual({row['id'] for row in detail['accounts']}, {str(self.primary.id), str(self.backup.id)})
        for event in detail['events']:
            self.assertEqual(event['event'], 'credential.updated')
            self.assertFalse(event['requires_confirmation'])
            self.assertEqual(event['received_count'], 0)
            source = ApplicationAudit.objects.get(id=event['id'])
            self.assertEqual(source.event, AuditEvent.CREDENTIAL_REPUBLISHED)
            self.assertEqual(source.operator, self.admin.name)
            self.assertEqual(source.operation_id, cycle_id)
            self.assertEqual(source.credential_key, self.credential.account_key(source.account_id))
        self.credential.refresh_from_db()
        self.primary.refresh_from_db()
        self.backup.refresh_from_db()
        self.assertEqual(self.credential.revision, 1)
        self.assertEqual(self.primary.secret, 'primary-secret')
        self.assertEqual(self.backup.secret, 'backup-secret')
        self.assertEqual(detail['events'][0]['revision'], self.primary.version)
        self.assertFalse(ChangeSecretRecord.objects.exists())
        self.assertFalse(AutomationExecution.objects.exists())
        self.assertFalse(self.credential.rotation_records.exists())

    def test_new_cycles_keep_separate_receipts_with_the_same_revision(self):
        self.subscription()
        _, first = start(self.credential.id)
        event = cycle_detail(self.credential, first)['events'][0]
        receive(self.client.id, self.org.id, event['id'])
        _, second = start(self.credential.id)
        self.assertNotEqual(first, second)
        self.assertEqual(cycle_directory(self.credential)['count'], 2)
        self.assertEqual(cycle_detail(self.credential, first)['events'][0]['received_count'], 1)
        self.assertTrue(all(row['received_count'] == 0 for row in cycle_detail(self.credential, second)['events']))

    def test_publication_after_commit_uses_account_keys_and_frozen_targets(self):
        self.subscription()
        layer = AsyncMock()
        with patch('accounts.credential_client.events.get_channel_layer', return_value=layer):
            with self.captureOnCommitCallbacks(execute=True):
                _, cycle_id = start(self.credential.id)
                layer.group_send.assert_not_called()
        self.assertEqual(layer.group_send.call_count, 2)
        for call in layer.group_send.call_args_list:
            payload = call.args[1]['payload']
            self.assertEqual(payload['operation_id'], str(cycle_id))
            self.assertEqual(call.args[1]['recipient_ids'], [str(self.client.id)])
            self.assertEqual(payload['credential_key'], self.credential.account_key(payload['account_id']))
            self.assertNotIn('secret', payload)

    def test_each_account_only_notifies_bound_applications_that_still_authorize_it(self):
        self.subscription()
        other = IntegrationApplication.objects.create(
            name='Restricted subscriber', accounts={'type': 'ids', 'ids': [str(self.primary.id)]},
        )
        CredentialApplicationBinding.objects.create(credential=self.credential, application=other)
        client = CredentialClientInstance.objects.create(application=other, instance_id='restricted')
        _, cycle_id = start(self.credential.id)
        for event in cycle_detail(self.credential, cycle_id)['events']:
            ids = {row['id'] for row in event['recipients']}
            self.assertIn(str(self.client.id), ids)
            self.assertEqual(str(client.id) in ids, event['account_id'] == str(self.primary.id))

    def test_legacy_all_authorized_scope_and_revocation_are_respected(self):
        self.subscription()
        self.credential.subscription_accounts.clear()
        self.credential.subscription_all_authorized = True
        self.credential.save(update_fields=['subscription_all_authorized'])
        _, first = start(self.credential.id)
        self.assertEqual(cycle_detail(self.credential, first)['event_count'], 2)
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save(update_fields=['accounts'])
        _, second = start(self.credential.id)
        self.assertEqual(cycle_detail(self.credential, second)['event_count'], 1)
        self.assertEqual(cycle_detail(self.credential, second)['account']['id'], str(self.primary.id))

    def test_disabled_policy_or_missing_authorization_cannot_start(self):
        self.subscription()
        self.credential.is_active = False
        self.credential.save(update_fields=['is_active'])
        with self.assertRaises(JMSException):
            start(self.credential.id)
        self.credential.is_active = True
        self.credential.save(update_fields=['is_active'])
        self.application.is_active = False
        self.application.save(update_fields=['is_active'])
        with self.assertRaises(JMSException):
            start(self.credential.id)

    def test_running_secret_change_blocks_republication(self):
        self.subscription()
        execution = AutomationExecution.objects.create(snapshot={})
        ChangeSecretRecord.objects.create(
            account=self.primary, asset=self.asset, execution=execution,
            old_secret=self.primary.secret, new_secret='candidate-secret', status='running',
        )
        with self.assertRaises(JMSException):
            start(self.credential.id)
        self.assertFalse(ApplicationAudit.objects.filter(event=AuditEvent.CREDENTIAL_REPUBLISHED).exists())

    def test_rotation_new_cycle_starts_preparation_and_prevents_an_overlapping_cycle(self):
        credential, first = start(self.credential.id, self.admin.name, self.admin.id)
        self.assertEqual(credential.status, 'preparing')
        self.assertEqual(credential.active_account_id, self.primary.id)
        self.assertEqual(cycle_detail(credential, first)['kind'], 'rotation')
        with self.assertRaises(JMSException):
            start(self.credential.id)
        CredentialRotationManager(credential.id).cancel('Start another preparation')
        credential, second = start(credential.id, self.admin.name, self.admin.id)
        self.assertNotEqual(first, second)
        self.assertEqual(cycle_detail(credential, first)['status'], 'cancelled')
        self.assertEqual(cycle_detail(credential, second)['status'], 'preparing')

    def test_start_cycle_api_returns_the_new_cycle_and_respects_organization(self):
        self.subscription()
        view = ApplicationCredentialViewSet.as_view({'post': 'start_cycle'})
        response = view(self.request('post', '/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['credential']['id'], str(self.credential.id))
        self.assertEqual(cycle_detail(self.credential, response.data['cycle_id'])['kind'], 'subscription_refresh')
        ApplicationCredential.objects.filter(pk=self.credential.id).update(org_id=str(uuid4()))
        response = view(self.request('post', '/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 404)

    def test_start_cycle_requires_policy_change_permission(self):
        self.subscription()
        view = ApplicationCredentialViewSet.as_view({'post': 'start_cycle'})
        with patch.object(type(self.admin), 'has_perm', return_value=False):
            with transaction.atomic():
                response = view(self.request('post', '/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 403)
