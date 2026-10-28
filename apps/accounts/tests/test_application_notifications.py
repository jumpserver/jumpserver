from unittest.mock import patch

from django.test import override_settings
from rest_framework.exceptions import ValidationError

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.const import ApplicationEvent
from accounts.credential_client.event_results import report
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_client.service_scope import service_metadata
from accounts.models import (
    ApplicationAudit, ApplicationCredential, CredentialClientInstance,
    CredentialRotationEvent, IntegrationApplication,
)
from accounts.serializers.account.service import IntegrationApplicationSerializer
from accounts.tests.base import CredentialTestCase
from accounts.ws import CredentialEventConsumer
from django.utils import timezone


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ApplicationNotificationTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.credential.delete()
        self.manager = CredentialClientManager(self.application, instance_id='notifications')
        self.client = self.manager.client

    def enable(self, value=True):
        self.application.credential_notifications_enabled = value
        self.application.save(update_fields=['credential_notifications_enabled'])

    def change(self):
        self.primary.secret = 'changed-secret'
        self.primary.save()
        self.primary.refresh_from_db()
        audit = ApplicationAudit.objects.filter(
            account_id=self.primary.id, event='credential_published',
        ).latest('date_created')
        return CredentialRotationEvent.objects.get(source_event_id=audit.id)

    def snapshot(self):
        consumer = CredentialEventConsumer()
        consumer.client = self.client
        consumer.org_id = self.org.id
        return consumer.snapshot_payload()

    def history(self):
        response = IntegrationApplicationViewSet.as_view({'get': 'credential_events'})(
            self.request('get', '/credential-events/'), pk=self.application.id,
        )
        self.assertEqual(response.status_code, 200)
        return response.data['results']

    def test_default_off_still_allows_pull_and_records_domain_event(self):
        self.assertFalse(self.application.credential_notifications_enabled)
        with patch('accounts.credential_client.events._publish_stream') as publish, self.captureOnCommitCallbacks(execute=True):
            event = self.change()
        publish.assert_not_called()
        self.assertFalse(event.notification_enabled)
        self.assertEqual(event.recipients, [])
        self.assertEqual(self.manager.fetch(f'account:{self.primary.id}', '127.0.0.1')['account']['secret'], 'changed-secret')
        row = next(row for row in self.history() if row['id'] == str(event.source_event_id))
        self.assertFalse(row['notification_enabled'])
        self.assertEqual(row['account_id'], str(self.primary.id))

    def test_enabled_notifies_all_authorized_accounts_without_policies(self):
        self.enable()
        self.assertFalse(ApplicationCredential.objects.exists())
        event = self.change()
        self.assertTrue(event.notification_enabled)
        self.assertEqual([row['id'] for row in event.recipients], [str(self.client.id)])
        self.assertEqual(event.recipients[0]['account_revision'], self.primary.version)
        keys = self.manager.credential_keys(self.application)
        self.assertEqual(set(keys), {f'account:{self.primary.id}', f'account:{self.backup.id}'})
        metadata = self.manager.authorized_accounts()['accounts']
        self.assertTrue(all(row['credentials'][0]['mode'] == 'subscription' for row in metadata))

    def test_only_authorized_enabled_applications_receive_change(self):
        self.enable()
        other = IntegrationApplication.objects.create(name='other', accounts={'type': 'ids', 'ids': [str(self.backup.id)]}, credential_notifications_enabled=True)
        other_client = CredentialClientInstance.objects.create(application=other, instance_id='other', type='sdk')
        event = self.change()
        self.assertNotIn(str(other_client.id), [row['id'] for row in event.recipients])
        self.assertFalse(ApplicationAudit.objects.filter(id=event.source_event_id, application_relations__application_id=other.id).exists())

    def test_no_clients_event_remains_in_application_history(self):
        self.enable()
        self.client.delete()
        event = self.change()
        self.assertEqual(event.recipients, [])
        self.assertIn(str(event.source_event_id), [row['id'] for row in self.history()])

    def test_reconnect_catches_current_version_and_reuses_result_target(self):
        self.enable()
        self.change()
        first = self.snapshot()
        self.assertEqual(set(first['authorized_account_ids']), {str(self.primary.id), str(self.backup.id)})
        item = next(item for item in first['credentials'] if item['account_id'] == str(self.primary.id))
        again = next(item for item in self.snapshot()['credentials'] if item['account_id'] == str(self.primary.id))
        self.assertEqual(item['event_id'], again['event_id'])
        self.assertEqual(item['revision'], self.primary.version)

    def test_disabled_snapshot_preserves_authorization_and_rotation_independent(self):
        self.enable()
        self.enable(False)
        snapshot = self.snapshot()
        self.assertEqual(snapshot['credentials'], [])
        self.assertIn(str(self.primary.id), snapshot['authorized_account_ids'])
        self.assertEqual(self.manager.fetch_account(self.primary.id, '127.0.0.1')['account']['id'], str(self.primary.id))

    def test_authorization_revocation_publishes_with_notifications_off(self):
        with patch('accounts.credential_client.events._publish_stream') as publish, self.captureOnCommitCallbacks(execute=True):
            self.application.accounts = {'type': 'ids', 'ids': [str(self.backup.id)]}
            self.application.save(update_fields=['accounts'])
        self.assertIn(ApplicationEvent.APPLICATION_SCOPE_UPDATED, [call.args[1] for call in publish.call_args_list])
        self.assertNotIn(str(self.primary.id), self.snapshot()['authorized_account_ids'])

    def test_fetch_and_delivery_are_distinct_from_business_confirmation(self):
        self.enable()
        event = self.change()
        self.manager.fetch_account(self.primary.id, '127.0.0.1')
        event.refresh_from_db()
        self.assertIsNotNone(event.recipients[0]['fetched_at'])
        self.assertEqual(event.recipients[0]['status'], 'pending')
        self.assertTrue(report(self.client, event.source_event_id)['accepted'])
        self.assertFalse(report(self.client, event.source_event_id)['accepted'])
        row = next(row for row in self.history() if row['id'] == str(event.source_event_id))
        self.assertEqual(row['recipients'][0]['status'], 'success')
        self.assertIsNotNone(row['recipients'][0]['finished_at'])

    def test_old_event_cannot_confirm_a_new_account_version(self):
        self.enable()
        event = self.change()
        self.primary.secret = 'newer-secret'
        self.primary.save()
        with self.assertRaises(ValidationError):
            report(self.client, event.source_event_id)

    def test_agent_polling_works_without_notifications_or_policy(self):
        manager = CredentialClientManager(self.application, instance_id='agent-poll', client_type='agent')
        scope = {'keys': [], 'account_ids': [str(self.primary.id)], 'include_authorized': True, 'switch_account_ids': []}
        desired, metadata, _ = service_metadata(manager, scope, {}, {}, timezone.now())
        self.assertEqual(desired['credential_keys'], [f'account:{self.primary.id}'])
        self.assertTrue(metadata[0]['available'])
        self.assertTrue(metadata[0]['event_id'])
        reply = manager.sync_agent(delivery_scope=scope, delivered_credentials=[{'key': f'account:{self.primary.id}', 'revision': self.primary.version}])
        event = CredentialRotationEvent.objects.get(source_event_id=reply['credentials'][0]['event_id'])
        self.assertIsNotNone(event.recipients[0]['delivered_at'])
        self.assertEqual(event.recipients[0]['status'], 'pending')

    def test_setting_can_be_edited_without_changing_account_authorization(self):
        serializer = IntegrationApplicationSerializer(self.application, data={'credential_notifications_enabled': True}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertTrue(updated.credential_notifications_enabled)
        self.assertEqual(updated.get_accounts().count(), 2)

    def test_independent_subscription_is_not_a_policy_api_resource(self):
        response = ApplicationCredentialViewSet.as_view({'post': 'create'})(self.request('post', '/application-credentials/', {
            'name': 'old subscription', 'mode': 'subscription', 'applications': [str(self.application.id)], 'subscription_all_authorized': True,
        }))
        self.assertEqual(response.status_code, 400)
