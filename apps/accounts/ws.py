import asyncio
from io import BytesIO
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.handlers.asgi import ASGIRequest
from django.utils import timezone

from accounts.api.account.credential import (
    CredentialClientAgentAuthentication, CredentialClientServiceAuthentication,
)
from accounts.const import AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import configuration_group
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import CredentialClientInstance
from orgs.utils import tmp_to_org


class CredentialClientAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        authenticated = await self.authenticate(scope)
        if authenticated:
            scope.update(authenticated)
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def authenticate(self, scope):
        request_scope = dict(scope)
        request_scope['method'] = 'GET'
        request = ASGIRequest(request_scope, BytesIO())
        org_id = request.headers.get('X-JMS-ORG', '')
        params = parse_qs(scope.get('query_string', b'').decode())
        try:
            with tmp_to_org(org_id):
                result = None
                for backend in (
                    CredentialClientAgentAuthentication(),
                    CredentialClientServiceAuthentication(),
                ):
                    result = backend.authenticate(request)
                    if result:
                        break
                if not result:
                    return None
                user, _ = result
                manager = CredentialClientManager(
                    user,
                    (params.get('configuration_id') or [''])[0],
                    (params.get('instance_id') or [''])[0],
                )
                manager.update_client_metadata(
                    request.headers.get('X-JMS-Client-Version', ''),
                    int(request.headers.get('X-JMS-Protocol-Version', 0)),
                    int(request.headers.get('X-JMS-Config-Schema-Version', 0)),
                )
                return {
                    'credential_client': manager.client,
                    'credential_org_id': org_id,
                }
        except Exception:
            return None


class CredentialEventConsumer(AsyncJsonWebsocketConsumer):
    touch_interval = 60

    async def connect(self):
        self.client = self.scope.get('credential_client')
        self.org_id = self.scope.get('credential_org_id')
        if not self.client:
            await self.close(code=4401)
            return
        self.group = configuration_group(self.client.configuration_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.touch(AuditEvent.CREDENTIAL_STREAM_CONNECTED)
        await self.send_json(await self.snapshot())
        self.touch_task = asyncio.create_task(self.keep_online())

    async def disconnect(self, close_code):
        task = getattr(self, 'touch_task', None)
        if task:
            task.cancel()
        if getattr(self, 'group', None):
            await self.channel_layer.group_discard(self.group, self.channel_name)
        if getattr(self, 'client', None):
            await self.touch(AuditEvent.CREDENTIAL_STREAM_DISCONNECTED)

    async def keep_online(self):
        try:
            while True:
                await asyncio.sleep(self.touch_interval)
                await self.touch()
        except asyncio.CancelledError:
            pass

    @database_sync_to_async
    def touch(self, event=None):
        with tmp_to_org(self.org_id):
            now = timezone.now()
            CredentialClientInstance.objects.filter(
                id=self.client.id, is_active=True,
            ).update(date_last_seen=now)
            if event:
                record(event, client=self.client)

    @database_sync_to_async
    def snapshot(self):
        with tmp_to_org(self.org_id):
            configuration = self.client.configuration
            credentials = configuration.credentials.filter(
                is_active=True,
                applications=configuration.application,
            ).order_by('key')
            items = []
            for credential in credentials:
                if credential.mode == credential.Mode.subscription:
                    items.extend({
                        'key': credential.account_key(account.id),
                        'account_id': str(account.id),
                        'credential_mode': credential.mode,
                        'revision': account.version,
                    } for account in configuration.application.get_accounts().order_by('id'))
                elif credential.authorized_applications().filter(
                    id=configuration.application_id,
                ).exists():
                    items.append({
                        'key': credential.key,
                        'credential_mode': credential.mode,
                        'revision': credential.current_revision,
                    })
            return {'event': 'snapshot', 'credentials': items}

    async def receive_json(self, content, **kwargs):
        if content.get('event') == 'ping':
            await self.touch()
            await self.send_json({'event': 'pong'})

    async def credential_event(self, event):
        await self.send_json(event['payload'])
