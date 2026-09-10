import threading
from unittest.mock import Mock, patch

from django.db import transaction

from accounts.credential_client.manager import CredentialClientManager
from accounts.demos.python.jms_pam.agent import Agent
from accounts.models import Account, ApplicationAudit, ApplicationCredential, ClientAccessConfiguration
from accounts.serializers import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase


class CredentialRevisionTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.credential.type = 'fixed'
        self.credential.rotation_mode = ''
        self.credential.backup_account = None
        self.credential.revision = 8
        self.credential.save()

    def test_save_queryset_and_bulk_password_updates_publish_once(self):
        self.primary.secret = 'first-change'
        self.primary.save()
        Account.objects.filter(pk=self.primary.pk).update(secret='second-change')
        self.primary.refresh_from_db()
        self.primary.secret = 'third-change'
        Account.objects.bulk_update([self.primary], ['secret'])
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.current_revision, 11)
        revisions = list(ApplicationAudit.objects.filter(
            credential_id=self.credential.id, event='credential_published', revision__gt=8,
        ).order_by('revision').values_list('revision', flat=True))
        self.assertEqual(revisions, [9, 10, 11])

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
        for bulk in (False, True):
            with self.subTest(bulk=bulk), patch(
                'accounts.credential_client.audit_signals.notify_model_change',
                side_effect=RuntimeError('publication failed'),
            ):
                with self.assertRaises(RuntimeError), transaction.atomic():
                    if bulk:
                        Account.objects.filter(pk=self.primary.pk).update(secret='rolled-back')
                    else:
                        self.primary.secret = 'rolled-back'
                        self.primary.save()
            self.primary = Account.objects.get(pk=self.primary.pk)
            self.credential.refresh_from_db()
            self.assertEqual(self.primary.secret, original)
            self.assertEqual(self.credential.revision, 8)

    def test_rotation_password_save_does_not_publish(self):
        self.credential.type = 'rotation'
        self.credential.rotation_mode = 'single'
        self.credential.save()
        self.primary.secret = 'awaiting-verification'
        self.primary.save()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.current_revision, 8)

    def test_switch_account_uses_fresh_revision_and_agent_updates(self):
        configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Revision SDK', type='sdk',
        )
        configuration.credentials.add(self.credential)
        manager = CredentialClientManager(self.application, configuration.id, 'revision-client')
        # Account versions belong to separate accounts and must not determine publication order.
        Account._base_manager.filter(pk=self.primary.pk).update(version=50)
        first = manager.fetch(self.credential.key, '127.0.0.1')
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'primary_account': str(self.backup.id)}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # A password publication between validation and save must not be overwritten.
        self.primary.refresh_from_db()
        self.primary.secret = 'intervening-change'
        self.primary.save()
        updated = serializer.save()
        self.assertEqual(updated.revision, 10)
        second = manager.fetch(self.credential.key, '127.0.0.1')
        self.assertEqual(second['revision'], 10)
        self.assertEqual(second['account']['id'], str(self.backup.id))
        manager.confirm(self.credential.key, second['revision'], self.backup.id)

        agent = object.__new__(Agent)
        agent.lock = threading.Lock()
        agent.config = {'credential_keys': [self.credential.key]}
        agent.credentials = {}
        agent.state = {}
        agent.remote = Mock()
        agent.remote.get_credential.side_effect = [first, second, second]
        with patch('accounts.demos.python.jms_pam.agent.atomic_write_json') as write:
            agent.poll()
            agent.poll()
            agent.poll()
        self.assertEqual(write.call_count, 2)
        self.assertEqual(agent.credentials[self.credential.key]['account_id'], str(self.backup.id))
        self.assertEqual(agent.credentials[self.credential.key]['secret'], self.backup.secret)
