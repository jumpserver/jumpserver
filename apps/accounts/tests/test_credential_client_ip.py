from unittest.mock import patch

from django.test import override_settings

from accounts.credential_client.manager import CredentialClientManager
from accounts.models import CredentialClientInstance
from accounts.serializers import CredentialClientInstanceSerializer
from accounts.tests import test_application_access as access_tests
from accounts.tests.base import CredentialTestCase


@override_settings(TRUSTED_IP_VERIFY_ENABLED=False)
class CredentialClientIPTests(CredentialTestCase):
    def connect(self, address, *, forwarded='', source='jms-pam'):
        original = self.factory.get

        def request(*args, **kwargs):
            kwargs['REMOTE_ADDR'] = address
            if forwarded:
                kwargs['HTTP_X_FORWARDED_FOR'] = forwarded
            return original(*args, **kwargs)

        with patch.object(self.factory, 'get', side_effect=request):
            return access_tests.ApplicationAccessTests.signed_request(
                self, 'client', {'instance_id': 'same-instance'}, source=source,
            )

    def test_sdk_and_agent_save_the_server_observed_address_independently(self):
        for source, kind, address in (
            ('jms-pam', 'sdk', '198.51.100.10'),
            ('jms-pam-agent', 'agent', '2001:db8::20'),
        ):
            response = self.connect(address, source=source)
            self.assertEqual(response.status_code, 200, response.data)
            client = CredentialClientInstance.objects.get(instance_id='same-instance', type=kind)
            self.assertEqual(client.remote_addr, address)
            self.assertEqual(CredentialClientInstanceSerializer(client).data['remote_addr'], address)
            self.assertIsNone(client.date_last_seen)

    def test_forwarded_ip_matches_the_application_allowlist_and_updates_on_reconnect(self):
        self.application.ip_group = ['203.0.113.10', '203.0.113.11']
        self.application.save(update_fields=['ip_group'])
        for address in self.application.ip_group:
            response = self.connect('127.0.0.1', forwarded=f'{address}, 10.0.0.1')
            self.assertEqual(response.status_code, 200, response.data)
            client = CredentialClientInstance.objects.get(instance_id='same-instance')
            self.assertEqual(client.remote_addr, address)

    def test_an_address_rejected_by_the_allowlist_does_not_replace_the_last_ip(self):
        self.application.ip_group = ['203.0.113.10']
        self.application.save(update_fields=['ip_group'])
        self.assertEqual(self.connect('203.0.113.10').status_code, 200)
        self.assertNotEqual(self.connect('203.0.113.11').status_code, 200)
        client = CredentialClientInstance.objects.get(instance_id='same-instance')
        self.assertEqual(client.remote_addr, '203.0.113.10')

    def test_missing_or_malformed_addresses_do_not_erase_a_known_ip(self):
        manager = CredentialClientManager(self.application, instance_id='ip-metadata')
        manager.update_client_metadata(remote_addr='2001:0db8:0:0:0:0:0:7')
        for value in (None, '', 'not-an-ip'):
            manager.update_client_metadata(remote_addr=value)
        manager.client.refresh_from_db()
        self.assertEqual(manager.client.remote_addr, '2001:db8::7')

    def test_access_ip_is_read_only_in_the_admin_api(self):
        client = CredentialClientInstance.objects.create(
            application=self.application, instance_id='read-only-ip', type='sdk', remote_addr='198.51.100.1',
        )
        serializer = CredentialClientInstanceSerializer(client, data={'remote_addr': '198.51.100.2'}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('remote_addr', serializer.validated_data)
        self.assertTrue(serializer.fields['remote_addr'].read_only)
