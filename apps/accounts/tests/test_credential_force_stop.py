from accounts.api.account.credential import ApplicationCredentialViewSet
from accounts.credential_rotation import CredentialRotationManager
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import CredentialClientStatus
from common.exceptions import JMSException

from .base import CredentialTestCase


class CredentialForceStopTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.manager = CredentialRotationManager(self.credential.id)
        client = CredentialClientManager(self.application, instance_id='force-stop-test')
        fetched = client.fetch(self.credential.key, '127.0.0.1')
        client.confirm(self.credential.key, fetched['revision'], self.primary.id)
        self.manager.start()

    def test_force_stop_preserves_recovery_blockers_and_releases_policy(self):
        self.manager.cancel('Recover original account')
        self.credential.refresh_from_db()
        self.assertTrue(self.credential.get_blockers())
        credential = self.manager.force_stop('Simulated clients cannot confirm', self.admin.name)
        self.assertEqual(credential.status, 'idle')
        self.assertEqual(credential.active_account_id, self.primary.id)
        rotation = credential.rotation_records.first()
        self.assertEqual(rotation.status, 'cancelled')
        self.assertIsNotNone(rotation.date_finished)
        self.assertEqual(rotation.participant_snapshot['force_stop']['operator'], self.admin.name)
        self.assertGreater(rotation.participant_snapshot['summary']['blocking'], 0)
        self.assertFalse(CredentialClientStatus.objects.filter(
            binding__credential=credential, is_rotation_participant=True,
        ).exists())
        self.manager.start()

    def test_cannot_force_stop_before_cancellation(self):
        with self.assertRaises(JMSException):
            self.manager.force_stop('Stop')
        self.credential.refresh_from_db()
        self.assertEqual(self.credential.status, 'waiting_switch')

    def test_force_stop_requires_reason(self):
        self.manager.cancel('Cancel')
        view = ApplicationCredentialViewSet.as_view({'post': 'force_stop_rotation'})
        for data in ({}, {'reason': ''}, {'reason': '   '}):
            response = view(self.request('post', '/', data), pk=self.credential.id)
            self.assertEqual(response.status_code, 400)

    def test_force_stop_api_allows_deleting_policy(self):
        self.manager.cancel('Cancel')
        view = ApplicationCredentialViewSet.as_view({'post': 'force_stop_rotation'})
        response = view(self.request('post', '/', {'reason': 'Remove test policy'}), pk=self.credential.id)
        self.assertEqual(response.status_code, 200)
        destroy = ApplicationCredentialViewSet.as_view({'delete': 'destroy'})
        response = destroy(self.request('delete', '/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 204)
