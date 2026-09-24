import threading
from unittest.mock import Mock, patch

from django.db import transaction

from accounts.credential_client.manager import CredentialClientManager
from accounts.demos.python.jms_pam.agent import Agent
from accounts.demos.python.jms_pam.credential.v1 import models
from accounts.models import (
    Account, ApplicationAudit, ApplicationCredential, AutomationExecution,
    ChangeSecretRecord, ClientAccessConfiguration,
)
from accounts.const import ChangeSecretRecordStatusChoice
from accounts.serializers import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase


class CredentialRevisionTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.credential.mode = ApplicationCredential.Mode.subscription
        self.credential.account = None
        self.credential.alternate_account = None
        self.credential.active_account = None
        self.credential.revision = 8
        self.credential.save()

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

    def test_subscription_uses_application_authorized_account_keys(self):
        configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Revision SDK', type='sdk',
        )
        configuration.credentials.add(self.credential)
        manager = CredentialClientManager(self.application, configuration.id, 'revision-client')
        primary_key = self.credential.account_key(self.primary.id)
        backup_key = self.credential.account_key(self.backup.id)
        self.assertSetEqual(
            set(CredentialClientManager.credential_keys(configuration)),
            {primary_key, backup_key},
        )
        first = manager.fetch('', '127.0.0.1', self.primary.id)
        self.primary.secret = 'intervening-change'
        self.primary.save()
        second = manager.fetch('', '127.0.0.1', self.primary.id)
        backup = manager.fetch(backup_key, '127.0.0.1')
        self.assertEqual(second['revision'], first['revision'] + 1)
        self.assertEqual(second['account']['id'], str(self.primary.id))
        self.assertEqual(backup['account']['id'], str(self.backup.id))

        agent = object.__new__(Agent)
        agent.lock = threading.Lock()
        agent.config = {'credential_keys': [primary_key]}
        agent.credentials = {}
        agent.state = {}
        agent.remote = Mock()
        agent.remote.GetCredential.side_effect = [
            models.GetCredentialResponse()._deserialize(item)
            for item in (first, second, second)
        ]
        with patch('accounts.demos.python.jms_pam.agent.atomic_write_json') as write:
            agent.fetch([primary_key])
            agent.fetch([primary_key])
            agent.fetch([primary_key])
        self.assertEqual(write.call_count, 2)
        self.assertEqual(agent.credentials[primary_key]['account_id'], str(self.primary.id))
        self.assertEqual(agent.credentials[primary_key]['secret'], self.primary.secret)
