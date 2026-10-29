from unittest.mock import patch

from accounts.const import ApplicationCommandEvent, ApplicationEvent, AuditEvent
from accounts.credential_client.events import _clients
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import (
    ApplicationAudit, CredentialApplicationBinding, CredentialRotationEvent,
    IntegrationApplication,
)
from accounts.models.application import default_application_webhook_events
from accounts.tests.base import CredentialTestCase
from accounts.ws import CredentialEventConsumer


class ApplicationScopeEventTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.client = CredentialClientManager(self.application, instance_id='scope-client').client

    def snapshot(self):
        consumer = CredentialEventConsumer()
        consumer.org_id, consumer.client = str(self.org.id), self.client
        return consumer.snapshot_payload()

    def test_unbinding_notifies_only_the_affected_application_and_preserves_account_access(self):
        other = IntegrationApplication.objects.create(
            name='Other scope', accounts=self.application.accounts.value,
        )
        CredentialApplicationBinding.objects.create(credential=self.credential, application=other)
        other_client = CredentialClientManager(other, instance_id='other-scope').client
        with patch('accounts.credential_client.events._publish_stream') as publish:
            with self.captureOnCommitCallbacks(execute=True):
                self.credential.applications.remove(self.application)
        self.assertEqual([call.args[1] for call in publish.call_args_list], [ApplicationEvent.APPLICATION_SCOPE_UPDATED])
        audit = ApplicationAudit.objects.get(id=publish.call_args.args[0])
        self.assertEqual(audit.event, AuditEvent.AUTHORIZATION_REVOKED)
        self.assertEqual(audit.credential_id, self.credential.id)
        self.assertEqual(list(_clients(audit, ApplicationEvent.APPLICATION_SCOPE_UPDATED)), [self.client])
        tracked = CredentialRotationEvent.objects.get(source_event_id=audit.id)
        self.assertEqual([item['id'] for item in tracked.recipients], [str(self.client.id)])
        self.assertNotIn(str(other_client.id), [item['id'] for item in tracked.recipients])
        self.assertEqual(self.snapshot()['credentials'], [])
        self.assertCountEqual(self.snapshot()['authorized_account_ids'], [str(self.primary.id), str(self.backup.id)])
        self.assertIsNotNone(self.application.get_account(account_id=self.primary.id))

    def test_policy_disable_uses_scope_update_and_preserves_authorized_accounts(self):
        with patch('accounts.credential_client.events._publish_stream') as publish:
            with self.captureOnCommitCallbacks(execute=True):
                self.credential.is_active = False
                self.credential.save(update_fields=['is_active'])
        self.assertEqual([call.args[1] for call in publish.call_args_list], [ApplicationEvent.APPLICATION_SCOPE_UPDATED])
        self.assertEqual(self.snapshot()['credentials'], [])
        self.assertCountEqual(self.snapshot()['authorized_account_ids'], [str(self.primary.id), str(self.backup.id)])

    def test_account_authorization_removal_uses_one_scope_event(self):
        with patch('accounts.credential_client.events._publish_stream') as publish:
            with self.captureOnCommitCallbacks(execute=True):
                self.application.accounts = {'type': 'ids', 'ids': [str(self.backup.id)]}
                self.application.save(update_fields=['accounts'])
        self.assertEqual([call.args[1] for call in publish.call_args_list], [ApplicationEvent.APPLICATION_SCOPE_UPDATED])
        self.assertEqual(self.snapshot()['authorized_account_ids'], [str(self.backup.id)])
        self.assertEqual(self.snapshot()['credentials'], [])
        self.assertIsNone(self.application.get_account(account_id=self.primary.id))

    def test_retired_revocation_is_not_a_default_webhook_event(self):
        self.assertNotIn(ApplicationEvent.CREDENTIAL_REVOKED, default_application_webhook_events())
        self.assertIn(ApplicationEvent.APPLICATION_SCOPE_UPDATED, default_application_webhook_events())

    def test_legacy_command_name_is_accepted_and_normalized(self):
        from accounts.serializers.account.application_command import ApplicationCommandSerializer
        serializer = ApplicationCommandSerializer(data={
            'event': 'application.restart.requested', 'client_ids': [str(self.client.id)],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['event'], ApplicationCommandEvent.APPLICATION_RESTART_REQUESTED)
        self.assertEqual(serializer.validated_data['event'], 'app.restart.requested')

    def test_event_aliases_normalize_for_existing_subscriptions(self):
        for old, new in (
            ('rotation.verification.started', 'rotation.verify.started'),
            ('rotation.verification.skipped', 'rotation.verify.skipped'),
            ('rotation.waiting_for_application', 'rotation.waiting_for_app'),
            ('application.scope.updated', 'app.scope.updated'),
        ):
            self.assertEqual(ApplicationEvent.canonical(old), new)
