from uuid import uuid4

from accounts.credential_rotation import CredentialRotationManager
from accounts.models import (
    Account,
    CredentialClientInstance,
    CredentialClientStatus,
    IntegrationApplication,
)
from accounts.serializers import CredentialClientInstanceSerializer
from accounts.tests.base import CredentialTestCase
from accounts.tests.test_application_access import ApplicationAccessTests


class SDKStatusTests(CredentialTestCase):
    signed_request = ApplicationAccessTests.signed_request

    def report(self, **kwargs):
        return self.signed_request('report_status', {
            'instance_id': 'reporter', 'status': 'running',
            'account_ids': [str(self.primary.id)], **kwargs,
        })

    def test_report_is_a_complete_usage_snapshot_without_rotation_confirmation(self):
        self.credential.status = 'waiting_switch'
        self.credential.save(update_fields=['status'])
        response = self.report(account_ids=[str(self.primary.id), str(self.backup.id)])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {'accepted': True})
        self.assertEqual(response['Cache-Control'], 'no-store')
        client = CredentialClientInstance.objects.get(instance_id='reporter', application=self.application)
        self.assertTrue(client.online)
        self.assertEqual(client.application_status['account_ids'], [str(self.primary.id), str(self.backup.id)])
        self.assertIsNotNone(client.date_status_reported)
        self.assertFalse(CredentialClientStatus.objects.filter(client=client).exists())
        self.assertFalse(client.rotation_enabled)
        metadata = self.signed_request('client', {'instance_id': 'reporter'})
        self.assertEqual(metadata.data['application_status'], client.application_status)
        admin = CredentialClientInstanceSerializer(client).data
        self.assertEqual(admin['application_status'], client.application_status)
        self.assertEqual([value['id'] for value in admin['reported_accounts']], [str(self.primary.id), str(self.backup.id)])
        self.assertEqual(admin['reported_accounts'][0]['username'], self.primary.username)
        self.assertEqual(admin['reported_accounts'][0]['asset']['name'], self.asset.name)
        self.assertIn('date_status_reported', admin)
        cleared = self.report(status='stopped', account_ids=[])
        self.assertEqual(cleared.status_code, 200, cleared.data)
        client.refresh_from_db()
        self.assertEqual(client.application_status, {'status': 'stopped', 'account_ids': [], 'error_code': ''})

    def test_unauthorized_account_and_invalid_reports_do_not_overwrite_previous_snapshot(self):
        self.assertEqual(self.report().status_code, 200)
        unauthorized = Account.objects.create(name='unassigned', username='unassigned', asset=self.asset)
        response = self.report(account_ids=[str(unauthorized.id)])
        self.assertEqual(response.status_code, 403, response.data)
        for values in (
            {'status': 'unknown'}, {'account_ids': [str(self.primary.id)] * 2},
            {'account_ids': [str(uuid4()) for _ in range(201)]},
            {'account_ids': ['invalid']}, {'error_code': 'arbitrary secret or exception message'},
        ):
            response = self.report(**values)
            self.assertEqual(response.status_code, 400, response.data)
        client = CredentialClientInstance.objects.get(instance_id='reporter', application=self.application)
        self.assertEqual(client.application_status['account_ids'], [str(self.primary.id)])

    def test_reports_are_scoped_to_authenticated_application_and_instance(self):
        self.assertEqual(self.report().status_code, 200)
        other = IntegrationApplication.objects.create(name='Other report application', secret='synthetic-other')
        response = self.signed_request('report_status', {
            'instance_id': 'reporter', 'status': 'error', 'account_ids': [],
            'error_code': 'db_unavailable', 'app_id': str(self.application.id),
        }, identity=str(other.id), secret=other.secret)
        self.assertEqual(response.status_code, 200, response.data)
        first = CredentialClientInstance.objects.get(instance_id='reporter', application=self.application)
        second = CredentialClientInstance.objects.get(instance_id='reporter', application=other)
        self.assertEqual(first.application_status['status'], 'running')
        self.assertEqual(second.application_status['status'], 'error')
        first.is_active = False
        first.save(update_fields=['is_active'])
        self.assertEqual(self.report().status_code, 403)

    def test_metadata_queries_do_not_enroll_diagnostic_instances_in_rotation(self):
        self.credential.status = 'waiting_switch'
        self.credential.save(update_fields=['status'])
        for action in ('application', 'client', 'policies', 'policy', 'accounts'):
            params = {'instance_id': f'diagnostic-{action}'}
            if action == 'policy':
                params['key'] = self.credential.key
            response = self.signed_request(action, params)
            self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(CredentialClientStatus.objects.exists())
        # Diagnostic registrations must also stay out of the next rotation.
        self.credential.status = 'idle'
        self.credential.save(update_fields=['status'])
        CredentialRotationManager(self.credential.id)._publish(self.credential)
        self.assertFalse(CredentialClientStatus.objects.exists())
        response = self.signed_request('credential', {
            'instance_id': 'diagnostic-client', 'key': self.credential.key,
        })
        self.assertEqual(response.status_code, 200, response.data)
        client = CredentialClientInstance.objects.get(instance_id='diagnostic-client')
        self.assertTrue(client.rotation_enabled)
        self.assertTrue(CredentialClientStatus.objects.filter(client=client).exists())

    def test_agent_reports_with_application_identity_and_rejects_legacy_token(self):
        agent = CredentialClientInstance.objects.create(
            application=self.application, type='agent', instance_id='fixed-agent',
            secret='synthetic-agent-secret',
        )
        response = self.signed_request('report_status', {
            'instance_id': 'fixed-agent', 'status': 'running',
            'account_ids': [str(self.primary.id)],
        }, source='jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        agent.refresh_from_db()
        self.assertEqual(agent.application_status['account_ids'], [str(self.primary.id)])
        denied = self.signed_request('report_status', {
            'instance_id': 'ignored-identity', 'status': 'error', 'account_ids': [],
        }, source='jms-pam-agent', identity=str(agent.id), secret=agent.secret)
        self.assertEqual(denied.status_code, 401, denied.data)
        agent.refresh_from_db()
        self.assertEqual(agent.application_status['status'], 'running')
        self.assertFalse(CredentialClientInstance.objects.filter(instance_id='ignored-identity').exists())

    def test_reported_account_names_are_resolved_once_for_a_page(self):
        self.assertEqual(self.report().status_code, 200)
        self.assertEqual(self.report(instance_id='second', account_ids=[str(self.backup.id)]).status_code, 200)
        clients = list(CredentialClientInstance.objects.filter(application=self.application).order_by('instance_id'))
        serializer = CredentialClientInstanceSerializer(clients, many=True)
        with self.assertNumQueries(1):
            results = [serializer.child.get_reported_accounts(client) for client in clients]
        self.assertEqual([value[0]['id'] for value in results], [str(self.primary.id), str(self.backup.id)])
