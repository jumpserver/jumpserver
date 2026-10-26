from datetime import timedelta
from uuid import uuid4

from django.test import override_settings
from django.utils import timezone

from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue
from accounts.credential_rotation.cycles import cycle_detail, cycle_directory
from accounts.models import ApplicationAudit, ApplicationEventDelivery, CredentialRotationEvent, CredentialRotationRecord
from accounts.tasks.application_events import clean_application_records_period
from accounts.tests.base import CredentialTestCase


@override_settings(APPLICATION_RECORD_KEEP_DAYS=30)
class CredentialCycleRetentionTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        CredentialRotationEvent.objects.all().delete()
        self.old = timezone.now() - timedelta(days=40)
        self.event_number = 0

    def event(self, code, *, cycle_id=None, rotation=None, old=True, revision=1):
        audit = record(
            AuditEvent.CREDENTIAL_PUBLISHED, credential=self.credential,
            operation_id=cycle_id, revision=revision,
        )
        enqueue(audit, code, rotation=rotation)
        if old:
            self.event_number += 1
            occurred_at = self.old + timedelta(seconds=self.event_number)
            ApplicationAudit.objects.filter(id=audit.id).update(date_created=occurred_at)
            CredentialRotationEvent.objects.filter(source_event_id=audit.id).update(published_at=occurred_at)
        return audit

    def rotation(self, status='running', finished=None):
        return CredentialRotationRecord.objects.create(
            credential=self.credential, source_account=self.primary, target_account=self.backup,
            change_account=self.primary, change_account_version_at_start=self.primary.version,
            status=status, date_finished=finished,
        )

    def test_completed_subscription_is_deleted_with_all_source_audits(self):
        operation = uuid4()
        first = self.event(ApplicationEvent.CREDENTIAL_CHANGE_STARTED, cycle_id=operation)
        last = self.event(ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, cycle_id=operation)
        clean_application_records_period()
        self.assertFalse(CredentialRotationEvent.objects.filter(cycle_id=operation).exists())
        self.assertFalse(ApplicationAudit.objects.filter(id__in=[first.id, last.id]).exists())

    def test_recent_end_keeps_whole_cycle_and_its_old_audits(self):
        operation = uuid4()
        first = self.event(ApplicationEvent.CREDENTIAL_CHANGE_STARTED, cycle_id=operation)
        self.event(ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, cycle_id=operation, old=False)
        clean_application_records_period()
        self.assertTrue(ApplicationAudit.objects.filter(id=first.id).exists())
        self.assertEqual(cycle_detail(self.credential, operation)['event_count'], 2)

    def test_incomplete_and_failed_cycles_keep_their_audits(self):
        pending, failed = uuid4(), uuid4()
        self.event(ApplicationEvent.CREDENTIAL_CHANGE_STARTED, cycle_id=pending)
        first = self.event(ApplicationEvent.CREDENTIAL_CHANGE_STARTED, cycle_id=failed)
        self.event(ApplicationEvent.CREDENTIAL_CHANGE_FAILED, cycle_id=failed)
        clean_application_records_period()
        self.assertEqual(cycle_directory(self.credential)['count'], 2)
        self.assertTrue(ApplicationAudit.objects.filter(id=first.id).exists())

    def test_rotation_retention_starts_at_finish_and_preserves_active_and_failed_cycles(self):
        expired = self.rotation('success', self.old)
        self.event(ApplicationEvent.ROTATION_COMPLETED, rotation=expired)
        recent = self.rotation('cancelled', timezone.now())
        recent_audit = self.event(ApplicationEvent.ROTATION_COMPLETED, rotation=recent)
        running = self.rotation()
        active_audit = self.event(ApplicationEvent.ROTATION_STARTED, rotation=running)
        failed = self.rotation('failed', self.old)
        self.event(ApplicationEvent.ROTATION_FAILED, rotation=failed)
        clean_application_records_period()
        self.assertFalse(CredentialRotationRecord.objects.filter(id=expired.id).exists())
        self.assertEqual(CredentialRotationRecord.objects.count(), 3)
        self.assertEqual(ApplicationAudit.objects.filter(id__in=[recent_audit.id, active_audit.id]).count(), 2)

    def test_recent_event_prevents_deleting_a_finished_rotation(self):
        rotation = self.rotation('success', self.old)
        self.event(ApplicationEvent.ROTATION_STARTED, rotation=rotation)
        self.event(ApplicationEvent.ROTATION_COMPLETED, rotation=rotation, old=False)
        clean_application_records_period()
        self.assertEqual(rotation.events.count(), 2)

    def test_current_execution_reference_prevents_deleting_a_finished_rotation(self):
        from accounts.models import AutomationExecution
        execution = AutomationExecution.objects.create(snapshot={})
        rotation = self.rotation('success', self.old)
        rotation.change_execution = execution
        rotation.save(update_fields=['change_execution'])
        self.credential.change_execution = execution
        self.credential.save(update_fields=['change_execution'])
        self.event(ApplicationEvent.ROTATION_COMPLETED, rotation=rotation)
        clean_application_records_period()
        self.assertTrue(CredentialRotationRecord.objects.filter(id=rotation.id).exists())

    def test_confirmation_for_retained_revision_survives_even_without_rotation_id(self):
        source = self.event(ApplicationEvent.CREDENTIAL_UPDATED, old=False, revision=9)
        confirmation = record(
            AuditEvent.CREDENTIAL_CONFIRMED, credential=self.credential, revision=9,
        )
        unrelated = record(
            AuditEvent.CREDENTIAL_CONFIRMED, credential=self.credential, revision=8,
        )
        ApplicationAudit.objects.filter(id__in=[confirmation.id, unrelated.id]).update(date_created=self.old)
        clean_application_records_period()
        self.assertTrue(ApplicationAudit.objects.filter(id=source.id).exists())
        self.assertTrue(ApplicationAudit.objects.filter(id=confirmation.id).exists())
        self.assertFalse(ApplicationAudit.objects.filter(id=unrelated.id).exists())

    def test_cleanup_is_idempotent_and_removes_expired_standalone_events(self):
        audit = self.event(ApplicationEvent.CREDENTIAL_REVOKED)
        clean_application_records_period()
        clean_application_records_period()
        self.assertFalse(CredentialRotationEvent.objects.filter(source_event_id=audit.id).exists())
        self.assertFalse(ApplicationAudit.objects.filter(id=audit.id).exists())

    def delivery(self, source, status):
        audit = record(AuditEvent.CONFIGURATION_UPDATED, credential=self.credential)
        ApplicationAudit.objects.filter(id=audit.id).update(date_created=self.old)
        delivery = ApplicationEventDelivery.objects.create(
            event=source, audit=audit, status=status, expires_at=timezone.now() + timedelta(days=1),
        )
        ApplicationEventDelivery.objects.filter(id=delivery.id).update(date_created=self.old)
        return delivery

    def test_pending_delivery_preserves_whole_old_cycle(self):
        operation = uuid4()
        first = self.event(ApplicationEvent.CREDENTIAL_CHANGE_STARTED, cycle_id=operation)
        last = self.event(ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, cycle_id=operation)
        delivery = self.delivery(last, 'pending')
        clean_application_records_period()
        self.assertTrue(ApplicationEventDelivery.objects.filter(id=delivery.id).exists())
        self.assertEqual(cycle_detail(self.credential, operation)['event_count'], 2)
        self.assertTrue(ApplicationAudit.objects.filter(id=first.id).exists())

    def test_completed_delivery_for_a_retained_cycle_keeps_source_and_details(self):
        operation = uuid4()
        first = self.event(ApplicationEvent.CREDENTIAL_CHANGE_STARTED, cycle_id=operation)
        self.event(ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, cycle_id=operation, old=False)
        delivery = self.delivery(first, 'success')
        clean_application_records_period()
        self.assertTrue(ApplicationEventDelivery.objects.filter(id=delivery.id).exists())
        self.assertTrue(ApplicationAudit.objects.filter(id=delivery.audit_id).exists())
        self.assertEqual(cycle_detail(self.credential, operation)['event_count'], 2)

    def test_account_switch_grant_waiting_for_application_is_retained(self):
        audit = self.event(ApplicationEvent.CREDENTIAL_UPDATED)
        CredentialRotationEvent.objects.filter(source_event_id=audit.id).update(recipients=[{'status': 'pending'}])
        clean_application_records_period()
        self.assertTrue(CredentialRotationEvent.objects.filter(source_event_id=audit.id).exists())
        self.assertTrue(ApplicationAudit.objects.filter(id=audit.id).exists())
