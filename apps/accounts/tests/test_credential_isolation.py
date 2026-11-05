
from accounts.api.account.credential import CredentialClientViewSet
from accounts.clients.python.jms_pam.common.exception import JumpServerPAMSDKException
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import CredentialClientStatus
from accounts.tests.base import CredentialTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import force_authenticate


def http_error(code, status=403):
    return JumpServerPAMSDKException(
        code, 'request failed', status_code=status, detail='DO_NOT_LOG_SECRET',
    )




class ConfirmationIsolationTests(CredentialTestCase):
    def setUp(self):
        super().setUp()
        self.manager = CredentialClientManager(self.application, instance_id='instance')
        self.manager.fetch(self.credential.key, '127.0.0.1')

    def test_fetch_rejection_has_machine_readable_code(self):
        request = self.factory.get('/api/v1/accounts/credential-client/credential/', {
            'instance_id': 'instance', 'key': 'missing',
        }, HTTP_X_JMS_ORG=str(self.org.id), HTTP_X_JMS_CLIENT_VERSION='1.0.0',
            HTTP_X_JMS_PROTOCOL_VERSION='1', HTTP_X_JMS_CONFIG_SCHEMA_VERSION='0')
        force_authenticate(request, user=self.application)
        response = CredentialClientViewSet.as_view({'get': 'credential'})(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'credential_not_found')

    def test_bad_revision_is_not_confirmed(self):
        with self.assertRaises(ValidationError):
            self.manager.confirm(self.credential.key, 2, self.primary.id)
        state = CredentialClientStatus.objects.get(client=self.manager.client)
        self.assertNotEqual(state.applied_revision, 2)
