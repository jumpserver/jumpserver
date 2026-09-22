from unittest.mock import AsyncMock, Mock, patch

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from accounts.demos.python.jms_pam.common.credential import Credential
from accounts.demos.python.jms_pam.common.profile.client_profile import ClientProfile
from accounts.demos.python.jms_pam.credential.v1.credential_client import CredentialClient
from accounts.credential_client.events import _publish_stream
from accounts.models import (
    Account, ApplicationAudit, ApplicationCredential, ClientAccessConfiguration,
    CredentialApplicationBinding, CredentialClientInstance, IntegrationApplication,
)
from accounts.ws import CredentialClientAuthMiddleware, CredentialEventConsumer
from assets.const import Category
from assets.models import Asset, Platform
from orgs.models import Organization
from orgs.utils import set_current_org, set_to_root_org


@override_settings(CHANNEL_LAYERS={
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'},
})
class CredentialEventStreamTests(TransactionTestCase):
    def setUp(self):
        self.org = Organization.default()
        set_current_org(self.org)
        platform = Platform.objects.create(
            name='CredentialStreamPostgreSQL', category=Category.DATABASE,
            type='postgresql',
        )
        asset = Asset.objects.create(
            name='credential-stream-db', address='127.0.0.1', platform=platform,
        )
        self.account = Account.objects.create(
            name='app', username='app', asset=asset, secret='secret',
        )
        self.application = IntegrationApplication.objects.create(
            name='stream-app', secret='stream-secret',
            accounts={'type': 'ids', 'ids': [str(self.account.id)]},
        )
        self.credential = ApplicationCredential.objects.create(
            name='Stream policy', mode=ApplicationCredential.Mode.subscription,
        )
        CredentialApplicationBinding.objects.create(
            credential=self.credential, application=self.application,
        )
        self.configuration = ClientAccessConfiguration.objects.create(
            application=self.application, name='Stream SDK', type='sdk',
        )
        self.configuration.credentials.add(self.credential)

    def tearDown(self):
        set_to_root_org()
        super().tearDown()

    def _post_teardown(self):
        super()._post_teardown()
        Organization.expire_orgs_mapping()
        set_to_root_org()

    def test_signed_connection_receives_snapshot_and_updates_online_state(self):
        async_to_sync(self._run_connection)()
        client = CredentialClientInstance.objects.get(instance_id='stream-instance')
        self.assertIsNotNone(client.date_last_seen)
        self.assertTrue(ApplicationAudit.objects.filter(
            service_id=self.application.id, configuration_id=self.configuration.id,
            instance_id=client.instance_id, event='credential_stream_connected',
        ).exists())
        self.assertTrue(ApplicationAudit.objects.filter(
            service_id=self.application.id, configuration_id=self.configuration.id,
            instance_id=client.instance_id, event='credential_stream_disconnected',
        ).exists())

    def test_unsigned_connection_is_rejected(self):
        async_to_sync(self._run_unsigned_connection)()

    def test_published_event_includes_subscription_selector(self):
        event = ApplicationAudit.objects.create(
            event='credential_published', service_id=self.application.id,
            credential_id=self.credential.id,
            credential_key=self.credential.account_key(self.account.id),
            account_id=self.account.id, revision=self.account.version,
        )
        layer = Mock(group_send=AsyncMock())
        with patch('accounts.credential_client.events.get_channel_layer', return_value=layer):
            _publish_stream(event.id, 'credential.updated')
        payload = layer.group_send.await_args.args[1]['payload']
        self.assertEqual(payload['credential_mode'], ApplicationCredential.Mode.subscription)
        self.assertEqual(payload['account_id'], str(self.account.id))

    async def _run_unsigned_connection(self):
        app = CredentialClientAuthMiddleware(CredentialEventConsumer.as_asgi())
        communicator = WebsocketCommunicator(
            app,
            '/ws/accounts/credential-events/'
            f'?configuration_id={self.configuration.id}&instance_id=unsigned',
        )
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4401)

    async def _run_connection(self):
        sdk = CredentialClient(
            Credential(str(self.application.id), self.application.secret),
            'stream-instance',
            ClientProfile(
                endpoint='http://testserver', org_id=str(self.org.id),
                configuration_id=str(self.configuration.id),
            ),
        )
        headers = []
        for header in sdk._event_stream_headers():
            name, value = header.split(': ', 1)
            headers.append((name.lower().encode(), value.encode()))
        path = (
            '/ws/accounts/credential-events/'
            f'?configuration_id={self.configuration.id}&instance_id=stream-instance'
        )
        app = CredentialClientAuthMiddleware(CredentialEventConsumer.as_asgi())
        communicator = WebsocketCommunicator(app, path, headers=headers)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        snapshot = await communicator.receive_json_from()
        self.assertEqual(snapshot, {
            'event': 'snapshot',
            'credentials': [{
                'key': self.credential.account_key(self.account.id),
                'account_id': str(self.account.id),
                'credential_mode': ApplicationCredential.Mode.subscription,
                'revision': self.account.version,
            }],
        })
        await communicator.disconnect()
