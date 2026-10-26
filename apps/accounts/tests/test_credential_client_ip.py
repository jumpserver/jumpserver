from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.apps import apps
from django.db import connection
from django.test import override_settings

from accounts.credential_client.manager import CredentialClientManager
from accounts.models import ApplicationAudit, CredentialClientInstance, IntegrationApplication
from accounts.serializers import CredentialClientInstanceSerializer
from accounts.tests import test_application_access as access_tests
from accounts.tests.base import CredentialTestCase
from orgs.utils import tmp_to_root_org


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

    def test_backfill_matches_application_org_instance_and_client_type(self):
        sdk = CredentialClientInstance.objects.create(
            application=self.application, instance_id='historical', type='sdk',
        )
        agent = CredentialClientInstance.objects.create(
            application=self.application, instance_id='historical', type='agent',
        )
        other = IntegrationApplication.objects.create(name='Other IP application')
        values = dict(event='credential_fetched', service_id=self.application.id, instance_id='historical')
        ApplicationAudit.objects.create(**values, source='SDK', remote_addr='198.51.100.1')
        ApplicationAudit.objects.create(**values, source='Agent', remote_addr='2001:db8::1')
        ApplicationAudit.objects.create(**values, source='SDK', remote_addr='198.51.100.2')
        ApplicationAudit.objects.create(**values, source='SDK', result='failed', remote_addr='198.51.100.3')
        ApplicationAudit.objects.create(**values, source='Administrator', remote_addr='198.51.100.4')
        ApplicationAudit.objects.create(**{**values, 'service_id': other.id}, source='SDK', remote_addr='198.51.100.5')
        foreign = ApplicationAudit.objects.create(**values, source='SDK', remote_addr='198.51.100.6')
        ApplicationAudit.objects.filter(id=foreign.id).update(org_id=str(uuid4()))
        backfill = import_module('accounts.migrations.0025_credentialclientinstance_remote_addr').backfill_remote_addr
        with tmp_to_root_org():
            backfill(apps, SimpleNamespace(connection=connection))
        sdk.refresh_from_db()
        agent.refresh_from_db()
        self.assertEqual(sdk.remote_addr, '198.51.100.2')
        self.assertEqual(agent.remote_addr, '2001:db8::1')
        # Reapplying the backfill never overwrites a newly observed address.
        sdk.remote_addr = '203.0.113.9'
        sdk.save(update_fields=['remote_addr'])
        with tmp_to_root_org():
            backfill(apps, SimpleNamespace(connection=connection))
        sdk.refresh_from_db()
        self.assertEqual(sdk.remote_addr, '203.0.113.9')
