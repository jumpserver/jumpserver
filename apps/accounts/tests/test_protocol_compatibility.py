from inspect import unwrap
from unittest.mock import patch

from accounts.credential_client.protocol import SERVER_CAPABILITIES, supported_versions
from accounts.models import CredentialClientInstance, CredentialClientStatus
from accounts.serializers import CredentialClientInstanceSerializer
from accounts.tests.base import CredentialTestCase
from accounts.tests.test_application_access import ApplicationAccessTests
from accounts.ws import CredentialClientAuthMiddleware


class ProtocolCompatibilityTests(CredentialTestCase):
    signed_request = ApplicationAccessTests.signed_request

    def test_program_versions_do_not_force_a_wire_upgrade(self):
        for version in ('0.9.0', '1.0.2', '9.9.9'):
            response = self.signed_request('client', {'instance_id': 'compatible-' + version}, client_version=version)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['protocol_version'], 1)
            self.assertEqual(response.data['server_capabilities'], list(SERVER_CAPABILITIES))
            self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertFalse(CredentialClientStatus.objects.exists())
        self.assertFalse(CredentialClientInstance.objects.filter(rotation_enabled=True).exists())

    def test_unsupported_versions_explain_supported_formats(self):
        for options in (
            {'protocol': 2}, {'protocol': 0}, {'protocol': 'invalid'},
            {'source': 'jms-pam-agent', 'schema': '2'},
        ):
            response = self.signed_request('client', {'instance_id': 'unsupported'}, **options)
            self.assertEqual(response.status_code, 426, response.data)
            self.assertEqual(response.data['code'], 'client_upgrade_required')
            for key, value in supported_versions().items():
                self.assertEqual(response.data[key], value)
        self.assertFalse(CredentialClientInstance.objects.filter(instance_id='unsupported').exists())

    def test_websocket_and_admin_use_the_same_wire_baseline(self):
        middleware = CredentialClientAuthMiddleware(None)
        for source, protocol, schema, accepted in (
            ('jms-pam', 1, 0, True), ('jms-pam', 2, 0, False),
            ('jms-pam-agent', 1, 1, True), ('jms-pam-agent', 1, 2, False),
        ):
            instance = f'ws-{source}-{protocol}-{schema}'
            scope = {
                'type': 'websocket', 'path': '/ws/accounts/credential-events/',
                'query_string': f'instance_id={instance}'.encode(),
                'headers': [(name.lower().encode(), str(value).encode()) for name, value in {
                    'X-JMS-ORG': self.org.id, 'X-Source': source,
                    'X-JMS-Protocol-Version': protocol, 'X-JMS-Config-Schema-Version': schema,
                    'X-JMS-Client-Version': '9.9.9',
                }.items()],
            }
            with patch('accounts.ws.CredentialClientApplicationAgentAuthentication.authenticate', return_value=None), \
                    patch('accounts.ws.CredentialClientServiceAuthentication.authenticate', return_value=(self.application, None)):
                # Run the wrapped middleware function in this test transaction;
                # authentication itself is covered by signed HTTP tests.
                result = unwrap(CredentialClientAuthMiddleware.authenticate)(middleware, scope)
            self.assertEqual(bool(result), accepted)
            client = CredentialClientInstance(
                type='agent' if source == 'jms-pam-agent' else 'sdk',
                protocol_version=protocol, config_schema_version=schema,
            )
            self.assertEqual(CredentialClientInstanceSerializer.get_upgrade_required(client), not accepted)
