from datetime import timedelta
from unittest.mock import patch

from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_rotation.events import receive
from accounts.models import (
    ApplicationAudit,
    CredentialClientInstance,
    CredentialClientStatus,
    CredentialRotationEvent,
)
from accounts.tests.base import CredentialTestCase
from accounts.tests.test_application_access import ApplicationAccessTests
from django.utils import timezone


class AgentSubscriptionProgressTests(CredentialTestCase):
    signed_request = ApplicationAccessTests.signed_request

    def setUp(self):
        super().setUp()
        self.credential.mode = 'subscription'
        self.credential.account = self.credential.alternate_account = self.credential.active_account = None
        self.credential.save()
        self.credential.subscription_accounts.set([self.primary])
        self.key = self.credential.account_key(self.primary.id)

    def sync(self, **data):
        response = self.signed_request('sync_agent', {'instance_id': 'subscription-agent', **data}, source='jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def revisions(self, value=None):
        return [{'key': self.key, 'revision': self.primary.version if value is None else value}]

    def state(self):
        return CredentialClientStatus.objects.get(client__instance_id='subscription-agent', binding__credential=self.credential)

    def test_received_held_delivered_and_applied_are_distinct(self):
        initial = self.sync()
        instance = CredentialClientInstance.objects.get(instance_id='subscription-agent')
        event_id = initial['credentials'][0]['event_id']
        self.assertTrue(receive(instance.id, self.org.id, event_id))
        self.assertFalse(CredentialClientStatus.objects.filter(client=instance).exists())
        audits = ApplicationAudit.objects.filter(event='credential_fetched').count()
        self.sync(credentials=self.revisions())
        held = self.state()
        self.assertIsNotNone(held.date_fetched)  # Version zero is a valid first version.
        self.assertIsNone(held.date_delivered)
        self.assertIsNone(held.date_applied)
        self.sync(credentials=self.revisions(), delivered_credentials=self.revisions())
        delivered = self.state()
        self.assertEqual(delivered.date_fetched, held.date_fetched)
        self.assertIsNotNone(delivered.date_delivered)
        self.assertIsNone(delivered.date_applied)
        self.assertIsNone(delivered.applied_account_id)
        self.assertFalse(delivered.is_rotation_participant)
        self.assertIsNone(delivered.required_revision)
        self.assertEqual(ApplicationAudit.objects.filter(event='credential_fetched').count(), audits)
        event = CredentialRotationEvent.objects.get(source_event_id=event_id)
        self.assertEqual(event.recipients[0]['status'], 'pending')
        self.assertIsNotNone(event.recipients[0]['received_at'])

    def test_repeated_sync_does_not_rewrite_progress_timestamps(self):
        self.sync(credentials=self.revisions(), delivered_credentials=self.revisions())
        original = self.state()
        manager = CredentialClientManager(original.client)
        with patch('accounts.credential_client.manager.timezone.now', return_value=timezone.now() + timedelta(minutes=5)):
            manager.sync_agent(credentials=self.revisions(), delivered_credentials=self.revisions())
        current = self.state()
        self.assertEqual(current.date_fetched, original.date_fetched)
        self.assertEqual(current.date_delivered, original.date_delivered)
        self.assertEqual(current.date_updated, original.date_updated)

    def test_ordinary_pull_keeps_generic_auditing_without_subscription_progress(self):
        for source in ('jms-pam', 'jms-pam-agent'):
            response = self.signed_request('credential', {'instance_id': source, 'account_id': str(self.primary.id)}, source=source)
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(ApplicationAudit.objects.filter(event='credential_fetched', result='success').count(), 2)
        self.assertFalse(CredentialClientStatus.objects.exists())

    def test_new_version_advances_held_and_delivered_independently(self):
        self.sync(credentials=self.revisions(), delivered_credentials=self.revisions())
        original = self.state()
        old_revision = self.primary.version
        self.primary.secret = 'next-subscription-password'
        self.primary.save()
        self.primary.refresh_from_db()
        later = timezone.now() + timedelta(minutes=5)
        manager = CredentialClientManager(original.client)
        with patch('accounts.credential_client.manager.timezone.now', return_value=later):
            manager.sync_agent(credentials=self.revisions(old_revision), delivered_credentials=self.revisions(old_revision))
            stale = self.state()
            self.assertEqual(stale.date_updated, original.date_updated)
            manager.sync_agent(credentials=self.revisions(), delivered_credentials=self.revisions(old_revision))
            held = self.state()
            self.assertEqual(held.fetched_revision, self.primary.version)
            self.assertEqual(held.date_fetched, later)
            self.assertEqual(held.delivered_revision, old_revision)
            self.assertEqual(held.date_delivered, original.date_delivered)
            manager.sync_agent(credentials=self.revisions(), delivered_credentials=self.revisions())
        delivered = self.state()
        self.assertEqual(delivered.delivered_revision, self.primary.version)
        self.assertEqual(delivered.date_delivered, later)
        self.assertIsNone(delivered.date_applied)
        self.assertFalse(ApplicationAudit.objects.filter(event='credential_fetched').exists())

    def test_stale_future_and_delivery_only_reports_cannot_invent_progress(self):
        self.primary.secret = 'new-subscription-password'
        self.primary.save()
        self.primary.refresh_from_db()
        revision = self.primary.version
        for known in (revision - 1, revision + 1):
            self.sync(credentials=self.revisions(known), delivered_credentials=self.revisions(revision))
        self.sync(delivered_credentials=self.revisions(revision))
        self.assertFalse(CredentialClientStatus.objects.exists())
        self.sync(credentials=self.revisions())
        state = self.state()
        self.sync(credentials=self.revisions(), delivered_credentials=self.revisions(revision - 1))
        self.assertIsNone(self.state().date_delivered)
        self.assertEqual(self.state().date_fetched, state.date_fetched)

    def test_reports_outside_current_subscription_and_local_scope_are_ignored(self):
        other_key = self.credential.account_key(self.backup.id)
        reports = [{'key': other_key, 'revision': self.backup.version}, {'key': 'account:not-a-uuid', 'revision': 0}]
        self.sync(credentials=reports, delivered_credentials=reports)
        self.assertFalse(CredentialClientStatus.objects.exists())
        self.sync(credentials=self.revisions())
        previous = self.state()
        result = self.sync(credentials=self.revisions(), delivered_credentials=self.revisions(),
                           delivery_scope={'keys': [], 'account_ids': [str(self.backup.id)]})
        self.assertEqual(result['scope']['credential_keys'], [])
        current = self.state()
        self.assertEqual(current.date_fetched, previous.date_fetched)
        self.assertIsNone(current.date_delivered)

    def test_legacy_push_fetch_can_report_delivery_without_held_versions(self):
        response = self.signed_request('credential', {'instance_id': 'subscription-agent', 'key': self.key}, source='jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        fetched = self.state()
        self.sync(delivered_credentials=self.revisions())
        delivered = self.state()
        self.assertEqual(fetched.date_fetched, delivered.date_fetched)
        self.assertIsNotNone(delivered.date_delivered)

    def test_multiple_account_versions_do_not_oscillate_summary_on_heartbeat(self):
        self.credential.subscription_accounts.add(self.backup)
        self.backup.secret = 'second-account-new-password'
        self.backup.save()
        self.backup.refresh_from_db()
        versions = self.revisions() + [{'key': self.credential.account_key(self.backup.id), 'revision': self.backup.version}]
        self.sync(credentials=versions, delivered_credentials=versions)
        before = self.state()
        self.sync(credentials=list(reversed(versions)), delivered_credentials=list(reversed(versions)))
        after = self.state()
        self.assertEqual((before.fetched_revision, before.delivered_revision), (after.fetched_revision, after.delivered_revision))
        self.assertEqual((before.date_fetched, before.date_delivered, before.date_updated), (after.date_fetched, after.date_delivered, after.date_updated))
