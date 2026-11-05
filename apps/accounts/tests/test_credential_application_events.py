from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.event_results import report, snapshot_result_event
from accounts.credential_client.manager import CredentialClientManager
from accounts.credential_rotation.manual_cycles import start
from accounts.credential_rotation.manager import CredentialRotationManager
from accounts.models import ApplicationAudit, CredentialClientInstance, CredentialRotationEvent
from accounts.tests.base import CredentialTestCase


class CredentialApplicationEventTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.application.credential_notifications_enabled = True
        self.application.save(update_fields=['credential_notifications_enabled'])
        self.client = CredentialClientInstance.objects.create(
            application=self.application, instance_id='event-names', type='sdk',
        )
        CredentialRotationEvent.objects.all().delete()

    def test_secret_change_publishes_secret_update_without_a_switch(self):
        self.primary.secret = 'new-secret'
        self.primary.save()
        event = CredentialRotationEvent.objects.get(event=ApplicationEvent.CREDENTIAL_SECRET_UPDATED)
        audit = ApplicationAudit.objects.get(id=event.source_event_id)
        self.assertEqual(audit.event, AuditEvent.CREDENTIAL_SECRET_UPDATED)
        self.assertEqual(audit.account_id, self.primary.id)
        self.assertEqual(event.recipients[0]['account_id'], str(self.primary.id))
        self.assertFalse(CredentialRotationEvent.objects.filter(event=ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED).exists())

    def test_rotation_publication_and_cancellation_are_switch_events(self):
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        event = CredentialRotationEvent.objects.get(event=ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED)
        audit = ApplicationAudit.objects.get(id=event.source_event_id)
        self.assertEqual(audit.event, AuditEvent.CREDENTIAL_SWITCH_PUBLISHED)
        self.assertEqual(event.recipients[0]['account_id'], str(self.backup.id))
        manager.cancel('Return to the source account')
        returned = CredentialRotationEvent.objects.filter(
            event=ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED,
        ).order_by('-sequence').first()
        self.assertEqual(returned.recipients[0]['account_id'], str(self.primary.id))
        self.assertFalse(CredentialRotationEvent.objects.filter(event=ApplicationEvent.CREDENTIAL_SECRET_UPDATED).exists())

    def test_revision_without_account_switch_only_requests_a_refresh(self):
        self.credential.revision += 1
        self.credential.save(update_fields=['revision'])
        event = CredentialRotationEvent.objects.get(event=ApplicationEvent.CREDENTIAL_REFRESH_REQUESTED)
        self.assertEqual(ApplicationAudit.objects.get(id=event.source_event_id).event,
                         AuditEvent.CREDENTIAL_REFRESH_REQUESTED)
        self.assertEqual(event.recipients[0]['account_id'], str(self.primary.id))

    def test_manual_subscription_refresh_does_not_claim_a_secret_change(self):
        self.credential.mode = 'subscription'
        self.credential.save(update_fields=['mode'])
        self.credential.subscription_accounts.add(self.primary, self.backup)
        _, cycle_id = start(self.credential.id)
        events = CredentialRotationEvent.objects.filter(cycle_id=cycle_id)
        self.assertEqual(events.count(), 2)
        self.assertEqual(set(events.values_list('event', flat=True)),
                         {ApplicationEvent.CREDENTIAL_REFRESH_REQUESTED})

    def test_snapshot_is_a_refresh_and_all_application_events_accept_results(self):
        for code in ApplicationEvent.credential_application_events():
            with self.subTest(event=code):
                manager = CredentialClientManager(self.application, instance_id=code)
                event_id = snapshot_result_event(
                    manager.client, self.credential, self.primary, self.credential.revision,
                )
                event = CredentialRotationEvent.objects.get(source_event_id=event_id)
                self.assertEqual(event.event, ApplicationEvent.CREDENTIAL_REFRESH_REQUESTED)
                event.event = code
                event.save(update_fields=['event'])
                self.assertTrue(report(manager.client, event_id)['accepted'])
