import asyncio
from io import BytesIO
from urllib.parse import parse_qs

from accounts.api.account.credential import (
    CredentialClientApplicationAgentAuthentication,
    CredentialClientServiceAuthentication,
)
from accounts.const import AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import application_group
from accounts.credential_client.manager import CredentialClientManager
from accounts.models import CredentialClientInstance
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.handlers.asgi import ASGIRequest
from django.utils import timezone
from orgs.utils import tmp_to_org
from rest_framework.exceptions import PermissionDenied

from common.utils import get_logger

logger = get_logger(__name__)


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
                    CredentialClientApplicationAgentAuthentication(),
                    CredentialClientServiceAuthentication(),
                ):
                    result = backend.authenticate(request)
                    if result:
                        break
                if not result:
                    return None
                user, _ = result
                client_type = 'agent' if request.headers.get('X-Source') == 'jms-pam-agent' else 'sdk'
                protocol = int(request.headers.get('X-JMS-Protocol-Version', 0))
                schema = int(request.headers.get('X-JMS-Config-Schema-Version', 0))
                if protocol != 1 or (client_type == 'agent' and schema != 1):
                    return None
                manager = CredentialClientManager(
                    user,
                    instance_id=(params.get('instance_id') or [''])[0],
                    client_type=client_type,
                )
                manager.update_client_metadata(
                    request.headers.get('X-JMS-Client-Version', ''),
                    protocol, schema,
                )
                if manager.client.protocol_version != 1 or (
                    manager.client.type == 'agent' and manager.client.config_schema_version != 1
                ):
                    return None
                supports_receipts = request.headers.get('X-JMS-Event-Receipts') == '1'
                CredentialClientInstance.objects.filter(id=manager.client.id).update(
                    event_receipts_supported=supports_receipts,
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
        self.group = application_group(self.client.application_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.touch(AuditEvent.CREDENTIAL_STREAM_CONNECTED)
        await self.send_json(await self.snapshot())
        for command in await self.pending_commands():
            await self.send_json(command)
        self.touch_task = asyncio.create_task(self.keep_online())

    @database_sync_to_async
    def pending_commands(self):
        from accounts.credential_client.commands import pending
        with tmp_to_org(self.org_id):
            return pending(self.client)

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
            try:
                self.client.application.assert_account_limit()
            except PermissionDenied:
                return {'event': 'snapshot', 'credentials': []}
            credentials = self.client.application.application_credentials.filter(
                is_active=True,
            ).order_by('key')
            from accounts.credential_client.event_results import snapshot_result_event
            items = []
            subscribed_accounts = set()
            for credential in credentials:
                if credential.mode == credential.Mode.subscription:
                    accounts = self.client.application.get_accounts().order_by('id')
                    if not credential.subscription_all_authorized:
                        accounts = accounts.filter(
                            id__in=credential.subscription_accounts.values('id')
                        )
                    for account in accounts:
                        if account.id in subscribed_accounts:
                            continue
                        subscribed_accounts.add(account.id)
                        items.append({
                            'key': credential.account_key(account.id),
                            'account_id': str(account.id),
                            'credential_mode': credential.mode,
                            'revision': account.version,
                            'account_revision': account.version,
                            'event_id': snapshot_result_event(self.client, credential, account, account.version),
                        })
                elif credential.authorized_applications().filter(
                    id=self.client.application_id,
                ).exists():
                    item = {
                        'key': credential.key,
                        'credential_mode': credential.mode,
                        'revision': credential.current_revision,
                    }
                    if credential.account_switch:
                        item['account_switch'] = credential.account_switch
                        item['account_id'] = str(credential.active_account_id)
                    item['account_revision'] = credential.active_account.version
                    item['event_id'] = snapshot_result_event(
                        self.client, credential, credential.active_account, credential.current_revision,
                    )
                    items.append(item)
            return {'event': 'snapshot', 'credentials': items}

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            return
        if content.get('event') == 'ping':
            await self.touch()
            await self.send_json({'event': 'pong'})
        elif content.get('event') == 'received':
            await self.receive_event(content.get('event_id'))

    @database_sync_to_async
    def receive_event(self, event_id):
        from accounts.credential_rotation.events import receive
        try:
            with tmp_to_org(self.org_id):
                if not receive(self.client.id, self.org_id, event_id):
                    from accounts.credential_client.commands import (
                        receive as receive_command,
                    )
                    receive_command(self.client, event_id)
        except Exception:
            logger.warning('Cannot record event receipt for client %s.', self.client.id)

    async def credential_event(self, event):
        if 'recipient_ids' in event and str(self.client.id) not in event['recipient_ids']:
            return
        await self.send_json(event['payload'])
        if event['payload']['event'] in ('configuration.updated', 'credential.revoked') or (
            event['payload']['event'] == 'credential.updated'
            and event['payload'].get('credential_mode') == 'subscription'
            and not event['payload'].get('account_id')
        ):
            await self.send_json(await self.snapshot())
