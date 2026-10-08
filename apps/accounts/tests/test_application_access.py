import json
from datetime import timedelta
from email.utils import formatdate
from shlex import split
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import uuid4

import requests
from accounts.api.account.application import IntegrationApplicationViewSet
from accounts.api.account.credential import (
    ApplicationCredentialViewSet,
    CredentialClientInstanceViewSet,
    CredentialClientViewSet,
)
from accounts.clients.python.jms_pam.common.abstract_client import HTTPSignatureAuth
from accounts.clients.python.jms_pam.common.credential import Credential
from accounts.clients.python.jms_pam.common.profile.client_profile import ClientProfile
from accounts.clients.python.jms_pam.credential.v1.credential_client import (
    CredentialClient,
)
from accounts.credential_client.access import materials
from accounts.credential_client.documentation import sdk_example
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import (
    Account,
    ApplicationCredential,
    CredentialApplicationBinding,
    CredentialClientInstance,
    IntegrationApplication,
)
from accounts.serializers.account.credential import (
    ApplicationCredentialSerializer,
    CredentialAccessWizardSerializer,
)
from accounts.serializers.account.service import IntegrationApplicationSerializer
from accounts.tests import test_credential_event_stream as stream_tests
from accounts.tests.base import CredentialTestCase
from accounts.ws import CredentialClientAuthMiddleware, CredentialEventConsumer
from asgiref.sync import async_to_sync
from assets.models import Asset
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.db import transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from orgs.models import Organization
from orgs.utils import set_to_root_org, tmp_to_org
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny


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
        path = {'sync_agent': 'agent/sync', 'accounts': 'accounts'}.get(action, 'credential')
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
        compile(data['code'], 'application_example.py', 'exec')
        self.assertEqual(data['sdk_language'], 'python')
        self.assertIn('pip install /path/to/jumpserver/apps/accounts/clients/python', data['install_command'])
        self.assertNotIn('pip install --upgrade jms-pam', data['install_command'])
        self.assertIn('instance_id=instance_id', data['code'])
        self.assertRegex(data['instance_id'], r'^[0-9a-f]{32}$')
        config_globals = {}
        exec(data['config'], config_globals)
        self.assertEqual(config_globals['instance_id'], data['instance_id'])
        reused_config = {}
        exec(data['config'], reused_config)
        self.assertEqual(reused_config['instance_id'], data['instance_id'])
        generated_again = materials(self.application, self.parameters(), 'http://testserver')
        self.assertNotEqual(generated_again['instance_id'], data['instance_id'])
        with patch.dict('os.environ', {'JMS_INSTANCE_ID': 'explicit-instance'}):
            overridden = {}
            exec(data['config'], overridden)
        self.assertEqual(overridden['instance_id'], 'explicit-instance')
        self.assertNotIn('credential_ids', data['config'])
        self.assertEqual(CredentialClientInstance.objects.count(), 0)

    def test_sdk_wizard_generates_language_specific_identity_and_example(self):
        for language in ('go', 'java', 'node'):
            with self.subTest(language=language):
                data = materials(
                    self.application, self.parameters(sdk_language=language),
                    'http://testserver',
                )
                self.assertEqual(data['sdk_language'], language)
                self.assertEqual(data['filename'], 'jms_pam_config.sh')
                exports = {
                    name.removeprefix('export '): split(value)[0]
                    for name, value in (
                        line.split('=', 1) for line in data['config'].splitlines()
                        if line.startswith('export ') and not line.startswith('export JMS_INSTANCE_ID=')
                    )
                }
                self.assertEqual(exports['JMS_APP_ID'], str(self.application.id))
                self.assertEqual(exports['JMS_APP_SECRET'], self.application.secret)
                self.assertRegex(data['instance_id'], r'^[0-9a-f]{32}$')
                self.assertIn(
                    f'export JMS_INSTANCE_ID="${{JMS_INSTANCE_ID:-{data["instance_id"]}}}"',
                    data['config'],
                )
                self.assertIn('. ./jms_pam_config.sh', data['install_command'])
                expected_code = sdk_example(language)
                if language == 'node':
                    expected_code = expected_code.replace("require('./index')", "require('@jumpserver/pam')")
                self.assertEqual(data['code'], expected_code)
                self.assertFalse(CredentialClientInstance.objects.exists())

    def test_sdk_wizard_rejects_unsupported_language(self):
        serializer = CredentialAccessWizardSerializer(
            data={'type': 'sdk', 'sdk_language': 'curl'},
            context={'application': self.application},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('sdk_language', serializer.errors)

    def test_signed_sdk_registers_automatically_and_reuses_instance(self):
        params = {
            'key': self.credential.key, 'instance_id': 'automatic-sdk',
        }
        for _ in range(2):
            response = self.signed_request('credential', params)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['account']['secret'], self.primary.secret)
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

        client = CredentialClientInstance.objects.get()
        client.is_active = False
        client.save()
        self.assertEqual(self.signed_request('credential', params).status_code, 403)
        client.refresh_from_db()
        self.assertFalse(client.is_active)

    def test_api_binding_update_changes_existing_scope_without_new_client(self):
        manager = CredentialClientManager(self.application, instance_id='sdk')
        replacement = IntegrationApplication.objects.create(name='Replacement application', accounts=self.application.accounts.value)
        serializer = ApplicationCredentialSerializer(
            self.credential, data={'applications': [str(replacement.id)]}, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertFalse(manager.application.application_credentials.exists())
        with self.assertRaises(PermissionDenied):
            manager._get_credential(self.credential.key)
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_automatic_scope_follows_all_application_bindings(self):
        manager = CredentialClientManager(self.application, instance_id='sdk')
        other = ApplicationCredential.objects.create(name='New policy', mode='subscription')
        self.assertNotIn(other, manager.application.application_credentials.all())
        binding = CredentialApplicationBinding.objects.create(credential=other, application=self.application)
        self.assertSetEqual(set(manager.application.application_credentials.all()), {self.credential, other})
        binding.delete()
        self.assertEqual(list(manager.application.application_credentials.all()), [self.credential])
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_automatic_scope_does_not_grant_unbound_policy_access(self):
        other = ApplicationCredential.objects.create(name='Unbound', mode='subscription')
        response = self.signed_request('credential', {'key': other.key, 'instance_id': 'sdk'})
        self.assertEqual(response.status_code, 403)

    def test_pull_access_does_not_require_a_push_policy(self):
        self.application.credential_bindings.all().delete()
        response = self.signed_request('credential', {
            'account_id': str(self.backup.id), 'instance_id': 'pull-only',
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['key'], f'account:{self.backup.id}')
        self.assertEqual(response.data['account']['secret'], self.backup.secret)
        self.assertEqual(response.data['revision'], self.backup.version)

        response = self.signed_request('accounts', {
            'instance_id': 'pull-only', 'limit': 1, 'offset': 1,
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['accounts']), 1)
        self.assertEqual(response.data['accounts'][0]['credentials'], [])
        self.assertNotIn('secret', response.data['accounts'][0])

    def test_pull_rejects_accounts_outside_application_authorization(self):
        self.application.accounts = {'type': 'ids', 'ids': [str(self.primary.id)]}
        self.application.save(update_fields=['accounts'])
        response = self.signed_request('credential', {
            'account_id': str(self.backup.id), 'instance_id': 'restricted-pull',
        })
        self.assertEqual(response.status_code, 403)

    def test_new_application_has_no_implicit_pull_access(self):
        application = IntegrationApplication.objects.create(name='Empty pull scope')
        self.assertEqual(application.accounts.value, {'type': 'ids', 'ids': []})
        self.assertFalse(application.get_accounts().exists())

        serializer = IntegrationApplicationSerializer(data={'name': 'API empty pull scope'})
        serializer.is_valid(raise_exception=True)
        created = serializer.save()
        self.assertEqual(created.accounts.value, {'type': 'ids', 'ids': []})
        self.assertFalse(created.get_accounts().exists())

        serializer = IntegrationApplicationSerializer(data={
            'name': 'Explicit empty pull scope', 'accounts': {'type': 'ids', 'ids': []},
        })
        serializer.is_valid(raise_exception=True)
        self.assertFalse(serializer.save().get_accounts().exists())

    def test_application_pull_scope_limit_applies_to_every_scope_type(self):
        rejected_scopes = [
            {'type': 'ids', 'ids': [str(self.primary.id)] * 2},
            {'type': 'attrs', 'attrs': [{'name': 'name', 'value': None}]},
        ]
        for scope in rejected_scopes:
            with self.subTest(scope=scope):
                serializer = IntegrationApplicationSerializer(data={
                    'name': 'Restricted pull scope', 'accounts': scope,
                })
                self.assertFalse(serializer.is_valid())
                self.assertIn('accounts', serializer.errors)

        scopes = [
            {'type': 'ids', 'ids': [str(self.primary.id), str(self.backup.id)]},
            {'type': 'all'},
            {'type': 'attrs', 'attrs': [{'name': 'name', 'match': 'startswith', 'value': 'account-'}]},
        ]
        with override_settings(APPLICATION_ACCOUNT_SCOPE_LIMIT=1):
            for scope in scopes:
                with self.subTest(scope=scope):
                    serializer = IntegrationApplicationSerializer(data={
                        'name': 'Restricted scope', 'accounts': scope,
                    })
                    self.assertFalse(serializer.is_valid())
                    self.assertIn('accounts', serializer.errors)

        with override_settings(APPLICATION_ACCOUNT_SCOPE_LIMIT=2):
            for scope in scopes:
                with self.subTest(scope=scope):
                    serializer = IntegrationApplicationSerializer(data={
                        'name': 'Allowed scope', 'accounts': scope,
                    })
                    serializer.is_valid(raise_exception=True)

        with override_settings(APPLICATION_ACCOUNT_SCOPE_LIMIT=101):
            serializer = IntegrationApplicationSerializer(data={
                'name': 'Large account pull scope',
                'accounts': {'type': 'ids', 'ids': [str(uuid4()) for _ in range(101)]},
            })
            serializer.is_valid(raise_exception=True)

    def test_existing_all_scope_is_preserved_when_other_fields_change(self):
        self.application.accounts = {'type': 'all'}
        self.application.enforce_account_limit = False
        self.application.save(update_fields=['accounts', 'enforce_account_limit'])
        with override_settings(APPLICATION_ACCOUNT_SCOPE_LIMIT=1):
            serializer = IntegrationApplicationSerializer(
                self.application, data={'name': 'Renamed application', 'accounts': {'type': 'all'}},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            self.assertFalse(self.application.enforce_account_limit)
            response = self.signed_request('credential', {
                'account_id': str(self.primary.id), 'instance_id': 'legacy-all',
            })
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.application.accounts.value, {'type': 'all'})

    def test_existing_all_scope_is_limited_when_authorization_changes(self):
        self.application.accounts = {'type': 'all'}
        self.application.enforce_account_limit = False
        self.application.save(update_fields=['accounts', 'enforce_account_limit'])
        with override_settings(APPLICATION_ACCOUNT_SCOPE_LIMIT=1):
            serializer = IntegrationApplicationSerializer(self.application, data={
                'accounts': {'type': 'attrs', 'attrs': [
                    {'name': 'name', 'match': 'startswith', 'value': 'account-'}
                ]},
            }, partial=True)
            self.assertFalse(serializer.is_valid())
            self.assertIn('accounts', serializer.errors)

            serializer = IntegrationApplicationSerializer(self.application, data={
                'accounts': {'type': 'ids', 'ids': [str(self.primary.id)]},
            }, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            self.assertTrue(self.application.enforce_account_limit)

    def test_dynamic_scope_stops_secret_access_if_it_grows_past_limit(self):
        self.application.accounts = {'type': 'attrs', 'attrs': [
            {'name': 'name', 'match': 'startswith', 'value': 'account-a'}
        ]}
        self.application.save(update_fields=['accounts'])
        with override_settings(APPLICATION_ACCOUNT_SCOPE_LIMIT=1):
            response = self.signed_request('credential', {
                'account_id': str(self.primary.id), 'instance_id': 'within-limit',
            })
            self.assertEqual(response.status_code, 200, response.data)
            Account.objects.create(
                name='account-a-new', username='account-a-new', asset=self.asset,
                secret='new-secret',
            )
            response = self.signed_request('credential', {
                'account_id': str(self.primary.id), 'instance_id': 'over-limit',
            })
            self.assertEqual(response.status_code, 403, response.data)
            self.assertEqual(response.data['code'], 'application_account_limit_exceeded')
            response = self.signed_request('accounts', {'instance_id': 'over-limit'})
            self.assertEqual(response.status_code, 403, response.data)
            with self.assertRaises(PermissionDenied):
                CredentialClientManager.credential_keys(self.application)

    def test_all_pull_scope_stays_within_application_organization(self):
        other_org = Organization.objects.create(name='Other pull scope org')
        with tmp_to_org(other_org):
            other_asset = Asset.objects.create(
                name='other-pull-asset', address='127.0.0.2', platform=self.platform,
            )
            other_account = Account.objects.create(
                name='other-pull-account', username='other', asset=other_asset,
                secret='other-secret',
            )
        self.application.accounts = {'type': 'all'}
        self.application.save(update_fields=['accounts'])
        with tmp_to_org(Organization.root()):
            ids = set(self.application.get_accounts().values_list('id', flat=True))
            self.assertSetEqual(ids, {self.primary.id, self.backup.id})
            self.assertIsNone(self.application.get_account(account_id=other_account.id))

    def test_wizard_allows_application_without_policy_bindings(self):
        self.application.credential_bindings.all().delete()
        data = materials(self.application, self.parameters(), 'http://testserver')
        self.assertEqual(data['type'], 'sdk')
        manager = CredentialClientManager(self.application, instance_id='sdk')
        self.assertFalse(manager.application.application_credentials.exists())

    def test_agent_materials_use_local_delivery_without_creating_scope(self):
        params = self.parameters(type='agent', app_user='app')
        first = materials(self.application, params, 'http://testserver')
        second = materials(self.application, params, 'http://testserver')
        self.assertEqual(first, second)
        bootstrap = json.loads(first['config'])
        self.assertEqual(bootstrap['instance_id'], '<instance-id>')
        self.assertIn('--instance-id "$(hostname)"', first['install_command'])
        self.assertEqual(bootstrap['app_id'], str(self.application.id))
        self.assertEqual(bootstrap['app_secret'], self.application.secret)
        self.assertIn('--bootstrap jms_pam_agent.json', first['install_command'])
        self.assertNotIn('--token', first['install_command'])
        self.assertNotIn('python', first['install_command'])
        self.assertNotIn('/venv/', first['install_command'])
        self.assertEqual(first['service_name'], 'jms-pam-agent')
        self.assertEqual(first['agent_language'], 'go')
        self.assertIn('init-local', first['foreground_unix_command'])
        self.assertIn('run --local --config', first['foreground_unix_command'])
        self.assertIn('init-local', first['foreground_windows_command'])
        self.assertIn('run --local --config', first['foreground_windows_command'])
        self.assertIn('$env:COMPUTERNAME', first['foreground_windows_command'])
        self.assertFalse(CredentialClientInstance.objects.exists())
        changed = self.parameters(type='agent', app_user='other')
        self.assertIn('event_file', bootstrap)
        self.assertEqual(bootstrap['rules'], [])
        self.assertEqual(json.loads(materials(self.application, changed, 'http://testserver')['config'])['delivery']['app_user'], 'other')
        environment = self.parameters(
            type='agent', app_user='app', delivery_mode='environment',
            systemd_unit='app.service',
        )
        self.assertFalse(materials(self.application, environment, 'http://testserver')['foreground_windows_command'])

    def test_agent_application_signature_syncs_and_sdk_cannot_use_agent_scope(self):
        params = {'instance_id': 'application-agent', 'credentials': []}
        response = self.signed_request('sync_agent', params, 'jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['scope']['credential_keys'], [self.credential.key])
        self.assertEqual(CredentialClientInstance.objects.get().type, 'agent')
        scoped_params = {**params, 'delivery_scope': {'keys': [], 'account_ids': [str(self.primary.id)]}}
        response = self.signed_request('sync_agent', scoped_params, 'jms-pam-agent')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['credentials'][0]['account_switch'], self.credential.account_switch)
        self.assertEqual(CredentialClientInstance.objects.get().delivery_scope, scoped_params['delivery_scope'])
        response = self.signed_request('credential', {**params, 'key': self.credential.key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CredentialClientInstance.objects.count(), 2)

    def test_legacy_agent_signature_is_rejected(self):
        client = CredentialClientInstance.objects.create(application=self.application, instance_id='legacy', type='agent', secret='legacy-secret')
        response = self.signed_request('sync_agent', {}, 'jms-pam-agent', identity=str(client.id), secret=client.secret)
        self.assertEqual(response.status_code, 401, response.data)
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_wrong_agent_secret_and_old_schema_do_not_register_instance(self):
        params = {'instance_id': 'bad-agent'}
        self.assertEqual(self.signed_request('sync_agent', params, 'jms-pam-agent', secret='wrong').status_code, 401)
        self.assertEqual(self.signed_request('sync_agent', params, 'jms-pam-agent', schema='0').status_code, 426)
        self.assertFalse(CredentialClientInstance.objects.exists())

    def test_wizard_endpoint_returns_non_cacheable_materials(self):
        request = self.request('post', '/', {'type': 'sdk'})
        response = IntegrationApplicationViewSet.as_view({'post': 'access_materials'}, permission_classes=[AllowAny])(request, pk=self.application.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data['filename'], 'jms_pam_config.py')
        self.assertRegex(response.data['instance_id'], r'^[0-9a-f]{32}$')
        self.assertIn(response.data['instance_id'], response.data['config'])
        request = self.request('post', '/', {'type': 'sdk', 'sdk_language': 'go'})
        response = IntegrationApplicationViewSet.as_view({'post': 'access_materials'}, permission_classes=[AllowAny])(request, pk=self.application.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['sdk_language'], 'go')
        self.assertEqual(response.data['filename'], 'jms_pam_config.sh')
        self.assertRegex(response.data['instance_id'], r'^[0-9a-f]{32}$')
        self.assertIn(response.data['instance_id'], response.data['config'])
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_policy_application_counts_include_unfetched_instances_and_zero_connections(self):
        empty = IntegrationApplication.objects.create(name='No connections')
        CredentialApplicationBinding.objects.create(credential=self.credential, application=empty)
        for name, active, last_seen in (
            ('online', True, timezone.now()),
            ('offline', True, timezone.now() - timedelta(minutes=3)),
            ('disabled', False, timezone.now()),
        ):
            CredentialClientInstance.objects.create(application=self.application, instance_id=name, type='sdk', is_active=active, date_last_seen=last_seen)
        other = ApplicationCredential.objects.create(name='Other policy', mode='subscription')
        CredentialApplicationBinding.objects.create(credential=other, application=self.application)
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
        self.assertEqual(response.data['access_readiness']['instances_amount'], 3)
        self.assertEqual(response.data['access_readiness']['online_instances_amount'], 1)


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class ApplicationAccessStreamTests(TransactionTestCase):
    def setUp(self):
        stream_tests.CredentialEventStreamTests.setUp(self)

    def tearDown(self):
        set_to_root_org()
        super().tearDown()

    def _post_teardown(self):
        super()._post_teardown()
        Organization.expire_orgs_mapping()
        set_to_root_org()

    async def connect(self, source='jms-pam', schema=None, after_connect=None):
        sdk = CredentialClient(
            Credential(str(self.application.id), self.application.secret), 'automatic-stream',
            ClientProfile(endpoint='http://testserver', org_id=str(self.org.id), source=source),
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
        self.assertEqual(list(client.application.application_credentials.all()), [self.credential])

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
            for added, expected in ((True, 1), (False, 1)):
                await bind(added)
                for _ in range(8):
                    event = await communicator.receive_json_from()
                    if event['event'] == 'snapshot' and len(event['credentials']) == expected:
                        self.assertEqual(event['credentials'][0]['key'], f'account:{self.account.id}')
                        break
                else:
                    self.fail('Application binding did not update the live snapshot')

        self.assertTrue(async_to_sync(self.connect)(after_connect=observe)[0])
        self.assertEqual(CredentialClientInstance.objects.count(), 1)

    def test_agent_websocket_authenticates_with_application_ak_sk(self):
        self.assertTrue(async_to_sync(self.connect)('jms-pam-agent')[0])
        self.assertEqual(CredentialClientInstance.objects.get().type, 'agent')

    def test_invalid_agent_schema_rejects_connection_without_creating_instance(self):
        self.assertEqual(async_to_sync(self.connect)('jms-pam-agent', schema='0'), (False, 4401))
        self.assertFalse(CredentialClientInstance.objects.exists())
