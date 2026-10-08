from accounts.const import ApplicationEvent
from accounts.credential_client.event_results import report, snapshot_result_event
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import CredentialClientInstance, CredentialClientStatus, CredentialRotationEvent
from accounts.tests.base import CredentialTestCase
from rest_framework.exceptions import NotFound, ValidationError


class CredentialEventResultTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.manager = CredentialClientManager(self.application, instance_id='event-results')
        self.instance = self.manager.client

    def event(self):
        self.primary.refresh_from_db()
        return snapshot_result_event(self.instance, self.credential, self.primary, self.credential.revision)

    def test_fetch_and_receipt_do_not_apply_success_is_idempotent(self):
        event_id = self.event()
        self.manager.fetch('', '127.0.0.1', account_id=self.primary.id)
        state = CredentialClientStatus.objects.get(client=self.instance, binding__credential=self.credential)
        self.assertEqual(state.applied_revision, 0)
        self.assertTrue(report(self.instance, event_id)['accepted'])
        state.refresh_from_db()
        self.assertEqual(state.applied_revision, self.credential.revision)
        self.assertEqual(state.applied_account_id, self.primary.id)
        self.assertFalse(report(self.instance, event_id)['accepted'])

    def test_failure_keeps_applied_state_unchanged_and_can_retry(self):
        event_id = self.event()
        self.assertTrue(report(self.instance, event_id, 'failed', 'application_failed')['accepted'])
        self.assertFalse(CredentialClientStatus.objects.filter(client=self.instance, applied_revision__gt=0).exists())
        self.assertTrue(report(self.instance, event_id)['accepted'])

    def test_other_instance_cannot_confirm(self):
        event_id = self.event()
        other = CredentialClientInstance.objects.create(application=self.application, instance_id='other', type='sdk')
        with self.assertRaises(NotFound):
            report(other, event_id)

    def test_changed_account_secret_rejects_old_event(self):
        event_id = self.event()
        self.primary.secret = 'new-secret'
        self.primary.save()
        with self.assertRaises(ValidationError):
            report(self.instance, event_id)
        self.assertNotEqual(event_id, self.event())

    def test_changed_policy_rejects_old_event(self):
        event_id = self.event()
        self.credential.revision += 1
        self.credential.save(update_fields=['revision'])
        with self.assertRaises(ValidationError):
            report(self.instance, event_id)

    def test_snapshot_reuses_durable_target(self):
        event_id = self.event()
        self.assertEqual(self.event(), event_id)
        tracked = CredentialRotationEvent.objects.get(source_event_id=event_id)
        self.assertEqual(tracked.event, ApplicationEvent.CREDENTIAL_UPDATED)
        self.assertEqual(tracked.recipients[0]['account_revision'], self.primary.version)

    def test_subscription_event_freezes_its_own_account_version(self):
        from types import SimpleNamespace
        from accounts.credential_client.events import _recipients
        self.credential.mode = 'subscription'
        self.credential.save(update_fields=['mode'])
        event = SimpleNamespace(credential_id=self.credential.id, account_id=self.primary.id, revision=7)
        from unittest.mock import patch
        with patch('accounts.credential_client.events._clients', return_value=CredentialClientInstance.objects.filter(id=self.instance.id)):
            recipients = _recipients(event, ApplicationEvent.CREDENTIAL_UPDATED)
        self.assertEqual(recipients[0]['account_revision'], 7)
