from unittest.mock import patch

from accounts.const import ChangeSecretRecordStatusChoice
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import (
    Account,
    ApplicationAudit,
    ApplicationCredential,
    AutomationExecution,
    ChangeSecretRecord,
)
from accounts.serializers import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase
from django.db import transaction


class CredentialRevisionTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.credential.mode = ApplicationCredential.Mode.subscription
        self.credential.account = None
        self.credential.alternate_account = None
        self.credential.active_account = None
        self.credential.revision = 8
        self.credential.save()
        self.credential.subscription_accounts.set([self.primary, self.backup])

    def test_only_selected_account_publishes_and_can_be_fetched(self):
        from rest_framework.exceptions import PermissionDenied

        self.credential.subscription_accounts.set([self.primary])
        manager = CredentialClientManager(self.application, instance_id='selected-client')
        self.assertEqual(
            CredentialClientManager.credential_keys(self.application),
            [self.credential.account_key(self.primary.id)],
        )
        self.assertEqual(
            manager.fetch('', '127.0.0.1', self.backup.id)['key'],
            f'account:{self.backup.id}',
        )
        with self.assertRaises(PermissionDenied):
            manager.fetch(self.credential.account_key(self.backup.id), '127.0.0.1')
        before = self.credential.revision
        self.backup.secret = 'unsubscribed-change'
        self.backup.save()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.revision, before)

    def test_changing_selected_accounts_notifies_connected_configuration(self):
        from accounts.models import CredentialRotationEvent

        serializer = ApplicationCredentialSerializer(
            self.credential,
            data={'subscription_accounts': [str(self.primary.id)]}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(
            list(self.credential.subscription_accounts.values_list('id', flat=True)),
            [self.primary.id],
        )
        self.assertTrue(CredentialRotationEvent.objects.filter(
            event='configuration.updated', rotation__isnull=True,
            source_event_id__in=ApplicationAudit.objects.filter(
                credential_id=self.credential.id,
            ).values('id'),
        ).exists())

    def test_password_update_publishes_once(self):
        ApplicationAudit.objects.filter(
            credential_id=self.credential.id, event='credential_published',
        ).delete()
        self.primary.secret = 'first-change'
        self.primary.save()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.current_revision, 9)
        event = ApplicationAudit.objects.get(
            credential_id=self.credential.id, event='credential_published',
        )
        self.primary.refresh_from_db()
        self.assertEqual(event.credential_key, self.credential.account_key(self.primary.id))
        self.assertEqual(event.account_id, self.primary.id)
        self.assertEqual(event.revision, self.primary.version)

    def test_managed_password_change_completes_before_publication(self):
        ApplicationAudit.objects.filter(credential_id=self.credential.id).delete()
        execution = AutomationExecution.objects.create(
            snapshot={}, org_id=self.credential.org_id,
        )
        record = ChangeSecretRecord.objects.create(
            account=self.primary, asset=self.primary.asset, execution=execution,
            old_secret=self.primary.secret, new_secret='managed-secret',
        )
        self.primary.secret = record.new_secret
        self.primary.save()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.revision, 8)

        record.status = ChangeSecretRecordStatusChoice.success
        record.save(update_fields=['status'])
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.revision, 9)
        events = list(ApplicationAudit.objects.filter(
            credential_id=self.credential.id,
            event__in=['secret_change_completed', 'credential_published'],
        ).order_by('date_created', 'id').values_list('event', flat=True))
        self.assertEqual(events, ['secret_change_completed', 'credential_published'])

    def test_metadata_and_repeated_save_do_not_publish(self):
        self.primary.comment = 'metadata only'
        self.primary.save()
        self.primary.save()
        Account.objects.filter(pk=self.primary.pk).update(comment='updated metadata')
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'name': 'Renamed credential'}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.current_revision, 8)

    def test_password_and_publication_roll_back_together(self):
        original = self.primary.secret
        with patch(
            'accounts.credential_client.audit_signals.enqueue',
            side_effect=RuntimeError('publication failed'),
        ):
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.primary.secret = 'rolled-back'
                self.primary.save()
        self.primary = Account.objects.get(pk=self.primary.pk)
        self.credential.refresh_from_db()
        self.assertEqual(self.primary.secret, original)
        self.assertEqual(self.credential.revision, 8)

    def test_rotation_password_save_does_not_publish(self):
        self.credential.mode = ApplicationCredential.Mode.alternating_rotation
        self.credential.account = self.primary
        self.credential.alternate_account = self.backup
        self.credential.active_account = self.primary
        self.credential.save()
        self.primary.secret = 'awaiting-verification'
        self.primary.save()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.current_revision, 8)
