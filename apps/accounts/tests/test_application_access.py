import json
from datetime import timedelta
from email.utils import formatdate
from unittest.mock import patch
from urllib.parse import urlsplit

import requests
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.db import transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.permissions import AllowAny

from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.credential import (
    ApplicationCredentialViewSet, CredentialClientInstanceViewSet, CredentialClientViewSet,
)
from accounts.credential_client.access import materials, subscription_scope
from accounts.credential_client.manager import CredentialClientManager
from accounts.demos.python.jms_pam.common.abstract_client import HTTPSignatureAuth
from accounts.demos.python.jms_pam.common.credential import Credential
from accounts.demos.python.jms_pam.common.profile.client_profile import ClientProfile
from accounts.demos.python.jms_pam.credential.v1.credential_client import CredentialClient
from accounts.models import (
    ApplicationCredential, ClientAccessConfiguration, CredentialApplicationBinding,
    CredentialClientInstance, IntegrationApplication,
)
from accounts.serializers.account.credential import CredentialAccessWizardSerializer
from accounts.serializers.account.credential import ApplicationCredentialSerializer
from accounts.tests.base import CredentialTestCase
from accounts.tests import test_credential_event_stream as stream_tests
from accounts.ws import CredentialClientAuthMiddleware, CredentialEventConsumer
from orgs.models import Organization
from orgs.utils import set_to_root_org, tmp_to_org


class ApplicationAccessTests(CredentialTestCase):
    def parameters(self, **overrides):
        serializer = CredentialAccessWizardSerializer(
            data={'type': 'sdk', **overrides},
            context={'application': self.application},
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def signed_request(self, action, params, source='jms-pam', identity=None, secret=None, schema=None):
        method = 'POST' if action == 'sync_agent' else 'GET'
        path = 'agent/sync' if action == 'sync_agent' else 'credential'
        prepared = requests.Request(
            method, f'http://testserver/api/v1/accounts/credential-client/{path}/',
            params=params if method == 'GET' else None,
            json=params if method == 'POST' else None,
            headers={
                'Accept': 'application/json', 'Date': formatdate(usegmt=True),
                'X-JMS-ORG': str(self.org.id), 'X-Source': source,
                'X-JMS-Client-Version': '1.0.0', 'X-JMS-Protocol-Version': '1',
                'X-JMS-Config-Schema-Version': schema or ('1' if source == 'jms-pam-agent' else '0'),
            },
            auth=HTTPSignatureAuth(identity or str(self.application.id), secret or self.application.secret),
        ).prepare()
        headers = {f'HTTP_{key.upper().replace("-", "_")}': value for key, value in prepared.headers.items()}
        if method == 'GET':
            request = self.factory.get(prepared.path_url, **headers)
        else:
            headers.pop('HTTP_CONTENT_TYPE', None)
            request = self.factory.post(prepared.path_url, prepared.body, content_type='application/json', **headers)
        with patch('authentication.backends.drf.update_service_integration_last_used.delay'):
            with transaction.atomic():
                return CredentialClientViewSet.as_view({method.lower(): action})(request)

    def test_sdk_materials_require_no_configuration_and_create_no_instance(self):
        data = materials(self.application, self.parameters(), 'http://testserver')
        compile(data['config'], data['filename'], 'exec')
        self.assertNotIn('credential_ids', data['config'])
        self.assertNotIn('configuration_id', data['config'])
        self.assertEqual(ClientAccessConfiguration.objects.count(), 0)
        self.assertEqual(CredentialClientInstance.objects.count(), 0)

    def test_signed_sdk_registers_automatically_and_reuses_instance(self):
        params = {
            'key': self.credential.key, 'instance_id': 'automatic-sdk',
        }
        for _ in range(2):
            response = self.signed_request('credential', params)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['account']['secret'], self.primary.secret)
        self.assertEqual(ClientAccessConfiguration.objects.count(), 1)
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

        client = CredentialClientInstance.objects.get()
        client.is_active = False
        client.save()
        self.assertEqual(self.signed_request('credential', params).status_code, 403)
        client.refresh_from_db()
        self.assertFalse(client.is_active)

    def test_api_binding_update_changes_existing_scope_without_new_client(self):
        manager = CredentialClientManager(self.application, instance_id='sdk')
        legacy = ClientAccessConfiguration.objects.create(application=self.application, name='Legacy SDK', type='sdk')
        legacy.credentials.add(self.credential)
        replacement = IntegrationApplication.objects.create(name='Replacement application', accounts=self.application.accounts.value)
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'applications': [str(replacement.id)]}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertFalse(manager.configuration.credentials.exists())
        self.assertFalse(legacy.credentials.exists())
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_automatic_scope_follows_all_application_bindings(self):
        manager = CredentialClientManager(self.application, instance_id='sdk')
        other = ApplicationCredential.objects.create(name='New policy', mode='subscription')
        self.assertNotIn(other, manager.configuration.credentials.all())
        binding = CredentialApplicationBinding.objects.create(credential=other, application=self.application)
        self.assertSetEqual(set(manager.configuration.credentials.all()), {self.credential, other})
        binding.delete()
        self.assertEqual(list(manager.configuration.credentials.all()), [self.credential])
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_automatic_scope_does_not_grant_unbound_policy_access(self):
        other = ApplicationCredential.objects.create(name='Unbound', mode='subscription')
        response = self.signed_request('credential', {'key': other.key, 'instance_id': 'sdk'})
        self.assertEqual(response.status_code, 403)

    def test_wizard_allows_application_without_policy_bindings(self):
        self.application.credential_bindings.all().delete()
        data = materials(self.application, self.parameters(), 'http://testserver')
        self.assertEqual(data['type'], 'sdk')
        manager = CredentialClientManager(self.application, instance_id='sdk')
        self.assertFalse(manager.configuration.credentials.exists())

    def test_agent_materials_use_application_credentials_and_reuse_scope(self):
        params = self.parameters(type='agent', app_user='app')
        first = materials(self.application, params, 'http://testserver')
        second = materials(self.application, params, 'http://testserver')
        self.assertEqual(first, second)
        bootstrap = json.loads(first['config'])
        self.assertEqual(bootstrap['app_id'], str(self.application.id))
        self.assertEqual(bootstrap['app_secret'], self.application.secret)
        self.assertIn('--bootstrap jms_pam_agent.json', first['install_command'])
        self.assertNotIn('--token', first['install_command'])
        self.assertEqual(ClientAccessConfiguration.objects.count(), 1)
        self.assertFalse(CredentialClientInstance.objects.exists())
        changed = self.parameters(type='agent', app_user='other')
        self.assertNotEqual(json.loads(materials(self.application, changed, 'http://testserver')['config'])['configuration_id'], bootstrap['configuration_id'])

    def test_agent_application_signature_syncs_and_sdk_cannot_use_agent_scope(self):
        scope = subscription_scope(self.application, 'agent', app_user='app')
        params = {'configuration_id': str(scope.id), 'instance_id': 'application-agent', 'credentials': []}
        response = self.signed_request('sync_agent', params, 'jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['configuration']['credential_keys'], [self.credential.key])
        self.assertEqual(CredentialClientInstance.objects.get().type, 'agent')
        response = self.signed_request('credential', {**params, 'key': self.credential.key})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_legacy_agent_signature_remains_supported(self):
        scope = subscription_scope(self.application, 'agent', app_user='app')
        client = CredentialClientInstance.objects.create(application=self.application, configuration=scope, instance_id='legacy', type='agent', secret='legacy-secret')
        response = self.signed_request('sync_agent', {}, 'jms-pam-agent', identity=str(client.id), secret=client.secret)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_wrong_agent_secret_and_old_schema_do_not_register_instance(self):
        scope = subscription_scope(self.application, 'agent', app_user='app')
        params = {'configuration_id': str(scope.id), 'instance_id': 'bad-agent'}
        self.assertEqual(self.signed_request('sync_agent', params, 'jms-pam-agent', secret='wrong').status_code, 401)
        self.assertEqual(self.signed_request('sync_agent', params, 'jms-pam-agent', schema='0').status_code, 426)
        self.assertFalse(CredentialClientInstance.objects.exists())

    def test_wizard_endpoint_returns_non_cacheable_materials(self):
        request = self.request('post', '/', {'type': 'sdk'})
        response = IntegrationApplicationViewSet.as_view({'post': 'access_materials'}, permission_classes=[AllowAny])(request, pk=self.application.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data['filename'], 'jms_pam_config.py')

    def test_policy_application_counts_include_unfetched_instances_and_zero_connections(self):
        empty = IntegrationApplication.objects.create(name='No connections')
        CredentialApplicationBinding.objects.create(credential=self.credential, application=empty)
        scope = subscription_scope(self.application)
        for name, active, last_seen in (
            ('online', True, timezone.now()),
            ('offline', True, timezone.now() - timedelta(minutes=3)),
            ('disabled', False, timezone.now()),
        ):
            CredentialClientInstance.objects.create(application=self.application, configuration=scope, instance_id=name, type='sdk', is_active=active, date_last_seen=last_seen)
        other = ApplicationCredential.objects.create(name='Other policy', mode='subscription')
        CredentialApplicationBinding.objects.create(credential=other, application=self.application)
        unrelated = ClientAccessConfiguration.objects.create(application=self.application, name='Legacy other policy', type='sdk')
        unrelated.credentials.add(other)
        CredentialClientInstance.objects.create(application=self.application, configuration=unrelated, instance_id='unrelated', type='sdk', date_last_seen=timezone.now())
        response = ApplicationCredentialViewSet.as_view({'get': 'access_applications'})(self.request('get', '/'), pk=self.credential.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['applications_amount'], 2)
        self.assertEqual(response.data['instances_amount'], 3)
        self.assertEqual(response.data['online_instances_amount'], 1)
        self.assertEqual(next(item for item in response.data['results'] if item['id'] == str(empty.id))['instances_amount'], 0)
        response = CredentialClientInstanceViewSet.as_view({'get': 'list'})(self.request('get', '/', {'credential': str(self.credential.id), 'limit': 10}))
        self.assertEqual(response.data['count'], 3)
        self.assertIn(str(self.credential.id), {str(item['id']) for item in response.data['results'][0]['credentials']})
        response = IntegrationApplicationViewSet.as_view({'get': 'retrieve'})(self.request('get', '/'), pk=self.application.id)
        self.assertEqual(response.data['access_readiness']['instances_amount'], 4)
        self.assertEqual(response.data['access_readiness']['online_instances_amount'], 2)


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ApplicationAccessStreamTests(TransactionTestCase):
    def setUp(self):
        stream_tests.CredentialEventStreamTests.setUp(self)
        self.configuration.delete()

    def tearDown(self):
        set_to_root_org()
        super().tearDown()

    def _post_teardown(self):
        super()._post_teardown()
        Organization.expire_orgs_mapping()
        set_to_root_org()

    async def connect(self, source='jms-pam', configuration_id=None, schema=None, after_connect=None):
        sdk = CredentialClient(
            Credential(str(self.application.id), self.application.secret), 'automatic-stream',
            ClientProfile(endpoint='http://testserver', org_id=str(self.org.id), source=source,
                          configuration_id=configuration_id),
        )
        if schema is not None:
            prepared = requests.Request('GET', sdk._event_stream_url().replace('ws://', 'http://'), headers={
                'Accept': 'application/json', 'Date': formatdate(usegmt=True), 'X-JMS-ORG': str(self.org.id),
                'X-Source': source, 'X-JMS-Client-Version': '1.0.0', 'X-JMS-Protocol-Version': '1',
                'X-JMS-Config-Schema-Version': schema,
            }, auth=sdk.auth).prepare()
            headers = [(key.lower().encode(), value.encode()) for key, value in prepared.headers.items()]
        else:
            headers = [(key.lower().encode(), value.encode()) for key, value in (header.split(': ', 1) for header in sdk._event_stream_headers())]
        path = urlsplit(sdk._event_stream_url())
        sdk.close()
        communicator = WebsocketCommunicator(CredentialClientAuthMiddleware(CredentialEventConsumer.as_asgi()), path.path + '?' + path.query, headers=headers)
        connected, code = await communicator.connect()
        if connected:
            snapshot = await communicator.receive_json_from()
            self.assertEqual(snapshot['credentials'][0]['account_id'], str(self.account.id))
            if after_connect:
                await after_connect(communicator)
        await communicator.disconnect()
        return connected, code

    def test_sdk_websocket_creates_scope_and_instance_on_connect(self):
        self.assertTrue(async_to_sync(self.connect)()[0])
        client = CredentialClientInstance.objects.get()
        self.assertEqual(client.type, 'sdk')
        self.assertTrue(client.online)
        self.assertEqual(list(client.configuration.credentials.all()), [self.credential])

    def test_existing_websocket_receives_new_bindings_and_revocations(self):
        @database_sync_to_async
        def bind(added):
            with tmp_to_org(self.org), transaction.atomic():
                if added:
                    credential = ApplicationCredential.objects.create(name='New bound policy', mode='subscription')
                    credential.subscription_accounts.add(self.account)
                    CredentialApplicationBinding.objects.create(credential=credential, application=self.application)
                else:
                    self.application.credential_bindings.filter(credential__name='New bound policy').delete()

        async def observe(communicator):
            for added, expected in ((True, 2), (False, 1)):
                await bind(added)
                for _ in range(8):
                    event = await communicator.receive_json_from()
                    if event['event'] == 'snapshot' and len(event['credentials']) == expected:
                        break
                else:
                    self.fail('Application binding did not update the live snapshot')

        self.assertTrue(async_to_sync(self.connect)(after_connect=observe)[0])
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_agent_websocket_authenticates_with_application_ak_sk(self):
        scope = subscription_scope(self.application, 'agent', app_user='app')
        self.assertTrue(async_to_sync(self.connect)('jms-pam-agent', str(scope.id))[0])
        self.assertEqual(CredentialClientInstance.objects.get().type, 'agent')

    def test_invalid_agent_schema_rejects_connection_without_creating_instance(self):
        scope = subscription_scope(self.application, 'agent', app_user='app')
        self.assertEqual(async_to_sync(self.connect)('jms-pam-agent', str(scope.id), '0'), (False, 4401))
        self.assertFalse(CredentialClientInstance.objects.exists())
