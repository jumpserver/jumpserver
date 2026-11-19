from uuid import uuid4
from unittest.mock import patch, PropertyMock

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.credential_client.event_results import report
from accounts.credential_client.manager import CredentialClientManager, client_uses_credential
from accounts.models import Account, ApplicationAudit, ApplicationCredential, CredentialClientInstance, CredentialClientStatus
from accounts.tests.base import CredentialTestCase
from accounts.tests.test_application_access import ApplicationAccessTests


class AgentServicesV1Tests(CredentialTestCase):
    signed_request = ApplicationAccessTests.signed_request

    def sync(self, *, accounts=(), switching=(), all_accounts=False, instance='services-v1', **extra):
        response = self.signed_request('sync_agent', {
            'instance_id': instance,
            'delivery_scope': {'keys': [], 'account_ids': list(accounts), 'include_authorized': True,
                               'all_authorized': all_accounts, 'switch_account_ids': list(switching)},
            **extra,
        }, source='jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['config_schema_version'], 1)
        self.assertIn('agent_store_services', response.data['server_capabilities'])
        return response.data

    def test_all_authorized_storage_does_not_require_push_or_join_rotation(self):
        self.application.credential_bindings.all().delete()
        result = self.sync(all_accounts=True)
        self.assertEqual(set(result['scope']['credential_keys']), {
            f'account:{self.primary.id}', f'account:{self.backup.id}',
        })
        self.assertEqual(result['scope']['confirmation_keys'], [])
        self.assertFalse(CredentialClientStatus.objects.exists())
        self.assertFalse(ApplicationAudit.objects.filter(event='credential_fetched').exists())
        self.assertNotIn('secret', str(result))
        self.assertTrue(all(item['available'] for item in result['credentials']))

    def test_fixed_account_and_switching_service_have_independent_scopes(self):
        fixed = self.sync(accounts=[str(self.primary.id)])
        self.assertEqual(fixed['scope']['credential_keys'], [f'account:{self.primary.id}'])
        client = CredentialClientInstance.objects.get(instance_id='services-v1')
        self.assertFalse(client_uses_credential(client, self.credential))
        switched = self.sync(switching=[str(self.primary.id)])
        self.assertEqual(switched['scope']['confirmation_keys'], [self.credential.key])
        item = switched['credentials'][0]
        self.assertEqual(item['account_id'], str(self.primary.id))
        self.assertEqual(item['account_switch'], self.credential.account_switch)
        client.refresh_from_db()
        self.assertTrue(client_uses_credential(client, self.credential))
        report(client, item['event_id'])
        self.assertEqual(CredentialClientStatus.objects.get(client=client).applied_revision, self.credential.revision)

    def test_skip_unblocks_rotation_without_recording_application_confirmation(self):
        from accounts.credential_rotation.manager import CredentialRotationManager
        from accounts.credential_rotation.cycles import cycle_detail
        from accounts.credential_rotation.participants import build

        self.sync(switching=[str(self.primary.id)])
        CredentialRotationManager(self.credential.id).start()
        self.credential.refresh_from_db()
        result = self.sync(switching=[str(self.primary.id)])
        item = next(row for row in result['credentials'] if row['key'] == self.credential.key)
        client = CredentialClientInstance.objects.get(instance_id='services-v1')
        client.date_last_seen = timezone.now()
        client.save(update_fields=['date_last_seen'])
        self.assertTrue(report(client, item['event_id'], 'skip')['accepted'])
        self.assertFalse(report(client, item['event_id'], 'skip')['accepted'])
        state = CredentialClientStatus.objects.get(client=client)
        self.assertTrue(state.confirmation_skipped)
        self.assertFalse(self.credential.get_blockers())
        self.assertEqual(build(self.credential)['instances'][0]['status'], 'skipped')
        self.assertEqual(build(self.credential)['applications'][0]['switched'], 0)
        self.assertEqual(build(self.credential)['applications'][0]['skipped'], 1)
        audits = ApplicationAudit.objects.filter(credential_id=self.credential.id, revision=self.credential.revision)
        self.assertTrue(audits.filter(event='credential_confirmation_skipped').exists())
        self.assertFalse(audits.filter(event='credential_confirmed').exists())
        detail = cycle_detail(self.credential, self.credential.rotation_records.first().id)
        event = next(row for row in detail['events'] if row['id'] == item['event_id'])
        self.assertEqual(event['skipped_count'], 1)
        self.assertEqual(event['confirmed_count'], 0)
        self.assertIsNotNone(event['recipients'][0]['skipped_at'])
        self.assertIsNone(event['recipients'][0]['confirmed_at'])
        # A later explicit check upgrades skip to a real confirmation.
        report(client, item['event_id'], 'success')
        state.refresh_from_db()
        self.assertFalse(state.confirmation_skipped)
        self.assertTrue(audits.filter(event='credential_confirmed').exists())

    def test_skip_rejects_superseded_account_versions(self):
        result = self.sync(switching=[str(self.primary.id)])
        item = result['credentials'][0]
        client = CredentialClientInstance.objects.get(instance_id='services-v1')
        self.credential.revision += 1
        self.credential.save(update_fields=['revision'])
        with self.assertRaises(ValidationError):
            report(client, item['event_id'], 'skip')
        self.assertFalse(CredentialClientStatus.objects.filter(client=client, confirmation_skipped=True).exists())

    def test_failure_requires_admin_review_even_after_successful_retry(self):
        from accounts.credential_rotation.manager import CredentialRotationManager
        from accounts.credential_rotation.cycles import cycle_detail
        from accounts.credential_rotation.participants import build
        self.sync(switching=[str(self.primary.id)])
        CredentialClientInstance.objects.update(date_last_seen=timezone.now())
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        item = next(row for row in self.sync(switching=[str(self.primary.id)])['credentials'] if row['key'] == self.credential.key)
        client = CredentialClientInstance.objects.get(instance_id='services-v1')
        report(client, item['event_id'], 'skip')
        manager.check_usage()
        report(client, item['event_id'], 'failed', 'application_failed')
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_switch')
        state = CredentialClientStatus.objects.get(client=client)
        failure = state.application_failure
        self.assertTrue(failure['review_required'])
        self.assertIsNone(build(self.credential)['source_traffic'])
        for result in ('skip', 'success'):
            report(client, item['event_id'], result)
            _, blockers = manager.check_usage()
            self.assertEqual(blockers[0]['reason'], 'review_required')
        with self.assertRaises(ValidationError):
            manager.review_application_failure(client.id, uuid4(), 'reviewed', self.admin.name)
        with self.assertRaises(ValidationError):
            manager.review_application_failure(client.id, failure['id'], ' ', self.admin.name)
        detail = cycle_detail(self.credential, self.credential.rotation_records.first().id)
        publication = next(row for row in detail['events'] if row['id'] == item['event_id'])
        self.assertEqual(publication['review_required_count'], 1)
        manager.review_application_failure(client.id, failure['id'], 'Validated the application manually', self.admin.name)
        self.assertFalse(self.credential.get_blockers())
        manager.check_usage()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'ready_for_change')
        state.refresh_from_db()
        self.assertFalse(state.application_failure['review_required'])
        self.assertEqual(state.application_failure['reviewed_by'], self.admin.name)
        self.assertEqual(ApplicationAudit.objects.filter(event='application_failure_reviewed').count(), 1)
        # Review requires administrative permission; a new failure cannot reuse an old approval.
        from accounts.api.account.credential import ApplicationCredentialViewSet
        from users.models import User
        view = ApplicationCredentialViewSet.as_view({'post': 'review_application_failure'})
        data = {'client_id': str(client.id), 'failure_id': failure['id'], 'reason': 'Reviewed'}
        outsider = User.objects.create_user(username='review-outsider', password='test-password')
        from django.db import transaction
        with transaction.atomic():
            response = view(self.request('post', '/review-application-failure/', data, user=outsider), pk=self.credential.id)
            self.assertEqual(response.status_code, 403)
        response = view(self.request('post', '/review-application-failure/', data), pk=self.credential.id)
        self.assertEqual(response.status_code, 200, response.data)
        report(client, item['event_id'], 'failed', 'failed_again')
        state.refresh_from_db()
        self.assertNotEqual(state.application_failure['id'], failure['id'])
        self.assertTrue(state.application_failure['review_required'])
        ApplicationCredential.objects.filter(pk=self.credential.pk).update(status='changing_secret')
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.get_blockers()[0]['reason'], 'review_required')
        with self.assertRaises(ValidationError):
            manager.review_application_failure(client.id, failure['id'], 'stale approval', self.admin.name)

    def test_admin_can_release_failed_result_without_fabricating_application_success(self):
        from accounts.credential_rotation.manager import CredentialRotationManager
        from accounts.credential_rotation.cycles import cycle_detail
        self.sync(switching=[str(self.primary.id)])
        CredentialClientInstance.objects.update(date_last_seen=timezone.now())
        manager = CredentialRotationManager(self.credential.id)
        manager.start()
        self.credential.refresh_from_db()
        item = next(row for row in self.sync(switching=[str(self.primary.id)])['credentials'] if row['key'] == self.credential.key)
        client = CredentialClientInstance.objects.get(instance_id='services-v1')
        report(client, item['event_id'], 'failed', 'application_failed')
        failure = CredentialClientStatus.objects.get(client=client).application_failure
        manager.review_application_failure(client.id, failure['id'], 'Proceed after manual review', self.admin.name)
        self.assertFalse(self.credential.get_blockers())
        detail = cycle_detail(self.credential, self.credential.rotation_records.first().id)
        event = next(row for row in detail['events'] if row['id'] == item['event_id'])
        self.assertEqual(event['recipients'][0]['status'], 'failed')
        self.assertEqual(event['admin_approved_count'], 1)
        self.assertEqual(event['confirmed_count'], 0)
        self.assertEqual(event['skipped_count'], 0)

    def test_failed_initial_delivery_requires_review_before_starting_rotation(self):
        from accounts.credential_rotation.manager import CredentialRotationManager
        from common.exceptions import JMSException
        item = next(row for row in self.sync(switching=[str(self.primary.id)])['credentials'] if row['key'] == self.credential.key)
        client = CredentialClientInstance.objects.get(instance_id='services-v1')
        report(client, item['event_id'], 'failed', 'initial_delivery_failed')
        manager = CredentialRotationManager(self.credential.id)
        with self.assertRaises(JMSException):
            manager.start()
        failure = CredentialClientStatus.objects.get(client=client).application_failure
        manager.review_application_failure(client.id, failure['id'], 'Initial delivery reviewed', self.admin.name)
        manager.start()
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_switch')

    def test_skipping_one_instance_does_not_resolve_other_instances(self):
        from accounts.credential_rotation.manager import CredentialRotationManager
        from accounts.credential_rotation.participants import build

        for name in ('first', 'second'):
            self.sync(switching=[str(self.primary.id)], instance=name)
        CredentialClientInstance.objects.update(date_last_seen=timezone.now())
        CredentialRotationManager(self.credential.id).start()
        self.credential.refresh_from_db()
        for index, name in enumerate(('first', 'second')):
            result = self.sync(switching=[str(self.primary.id)], instance=name)
            item = next(row for row in result['credentials'] if row['key'] == self.credential.key)
            client = CredentialClientInstance.objects.get(instance_id=name)
            report(client, item['event_id'], 'skip' if index == 0 else 'success')
            self.assertEqual(len(self.credential.get_blockers()), 1 if index == 0 else 0)
        progress = build(self.credential)
        self.assertEqual(progress['summary']['skipped'], 1)
        self.assertEqual(progress['summary']['switched'], 1)

    def test_unknown_switch_account_is_not_authorized_and_unassociated_account_is_fixed(self):
        third = Account.objects.create(name='third', username='third', asset=self.asset, secret='third-secret')
        self.application.accounts = {'type': 'ids', 'ids': [str(third.id)]}
        self.application.save()
        unknown = str(uuid4())
        result = self.sync(switching=[str(third.id), unknown])
        self.assertEqual(result['scope']['credential_keys'], [f'account:{third.id}'])
        self.assertEqual(result['scope']['confirmation_keys'], [])
        self.assertEqual(result['unavailable_switch_account_ids'], [unknown])

    def test_unbound_unauthorized_and_ambiguous_switches_never_fall_back(self):
        for change in ('unbound', 'unauthorized', 'ambiguous'):
            with self.subTest(change=change):
                if change == 'unbound':
                    self.credential.applications.remove(self.application)
                elif change == 'unauthorized':
                    self.credential.applications.add(self.application)
                    self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
                    self.application.save()
                else:
                    self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id), str(self.backup.id)]}
                    self.application.save()
                    duplicate = ApplicationCredential.objects.create(
                        name='ambiguous', mode='alternating_rotation', account=self.primary,
                        alternate_account=self.backup, active_account=self.primary,
                    )
                    duplicate.applications.add(self.application)
                result = self.sync(switching=[str(self.primary.id)])
                self.assertEqual(result['credentials'], [])
                self.assertEqual(result['unavailable_switch_account_ids'], [str(self.primary.id)])
                client = CredentialClientInstance.objects.get(instance_id='services-v1')
                self.assertFalse(client_uses_credential(client, self.credential))

    def test_storage_cannot_confirm_rotation_and_standby_is_unavailable_during_change(self):
        ApplicationCredential.objects.filter(pk=self.credential.pk).update(
            status='changing_secret', date_rotation_started=timezone.now(),
        )
        result = self.sync(all_accounts=True)
        items = {item['account_id']: item for item in result['credentials']}
        self.assertTrue(items[str(self.primary.id)]['available'])
        self.assertFalse(items[str(self.backup.id)]['available'])
        self.assertEqual(result['scope']['confirmation_keys'], [])
        self.assertFalse(CredentialClientStatus.objects.exists())

    def test_revocation_and_empty_declarations_remove_previous_keys(self):
        result = self.sync(all_accounts=True)
        known = [{'key': item['key'], 'revision': item['revision']} for item in result['credentials']]
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save()
        revoked = self.sync(all_accounts=True, credentials=known)
        self.assertEqual(revoked['removed_keys'], [f'account:{self.backup.id}'])
        empty = self.sync(credentials=known)
        self.assertEqual(empty['credentials'], [])
        self.assertEqual(set(empty['removed_keys']), {item['key'] for item in known})

    def test_scope_validation_requires_v1_account_selectors(self):
        for scope in (
            {'keys': [], 'account_ids': [], 'all_authorized': True},
            {'keys': [], 'account_ids': [], 'switch_account_ids': [str(self.primary.id)]},
            {'keys': [], 'account_ids': [], 'include_authorized': True,
             'switch_account_ids': [str(self.primary.id)] * 2},
            {'keys': [self.credential.key], 'account_ids': [], 'include_authorized': True},
        ):
            response = self.signed_request('sync_agent', {
                'instance_id': 'invalid-service', 'delivery_scope': scope,
            }, source='jms-pam-agent')
            self.assertEqual(response.status_code, 400, response.data)

    def test_missing_password_is_unavailable_without_fetching_vault_secrets(self):
        Account.objects.filter(pk=self.backup.pk).update(_secret=None)
        with patch.object(Account, 'secret', new_callable=PropertyMock, side_effect=AssertionError('metadata fetched a secret')):
            result = self.sync(all_accounts=True)
        items = {item['account_id']: item for item in result['credentials']}
        self.assertTrue(items[str(self.primary.id)]['available'])
        self.assertFalse(items[str(self.backup.id)]['available'])
        self.assertFalse(ApplicationAudit.objects.filter(event='credential_fetched').exists())
