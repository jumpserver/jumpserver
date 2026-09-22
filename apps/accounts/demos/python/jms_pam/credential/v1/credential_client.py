import json
import time
from email.utils import formatdate
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests
import websocket

from ... import CONFIG_SCHEMA_VERSION, PROTOCOL_VERSION, __version__
from ...common.abstract_client import AbstractClient
from . import models

CLIENT_PATH = '/api/v1/accounts/credential-client'


class CredentialClient(AbstractClient):
    def _call(self, method, path, request, request_type, response_type, query=False):
        if not isinstance(request, request_type):
            raise TypeError(f'request must be a {request_type.__name__}')
        return self._request(method, f'{CLIENT_PATH}/{path}/', request, response_type, query)

    def GetCredential(self, request):
        return self._call(
            'GET', 'credential', request, models.GetCredentialRequest,
            models.GetCredentialResponse, query=True,
        )

    def ConfirmCredential(self, request):
        return self._call(
            'POST', 'confirm', request, models.ConfirmCredentialRequest,
            models.ConfirmCredentialResponse,
        )

    def SyncAgent(self, request):
        return self._call(
            'POST', 'agent/sync', request, models.AgentSyncRequest,
            models.AgentSyncResponse,
        )

    def WatchCredentialEvents(self, stop_event=None):
        """Yield Credential Event Stream messages, reconnecting with bounded backoff."""
        delay = 1
        while not stop_event or not stop_event.is_set():
            connection = None
            try:
                connection = websocket.create_connection(
                    self._event_stream_url(),
                    header=self._event_stream_headers(),
                    timeout=self.profile.Timeout,
                )
                connection.settimeout(30)
                delay = 1
                while not stop_event or not stop_event.is_set():
                    try:
                        payload = connection.recv()
                    except websocket.WebSocketTimeoutException:
                        connection.ping()
                        continue
                    if not payload:
                        break
                    event = json.loads(payload)
                    if not isinstance(event, dict) or 'event' not in event:
                        raise ValueError('Invalid credential event message.')
                    yield event
            except (OSError, ValueError, websocket.WebSocketException):
                if stop_event and stop_event.wait(delay):
                    return
                if not stop_event:
                    time.sleep(delay)
                delay = min(delay * 2, 30)
            finally:
                if connection:
                    connection.close()

    def _event_stream_url(self):
        endpoint = urlsplit(self.profile.Endpoint)
        scheme = 'wss' if endpoint.scheme == 'https' else 'ws'
        query = urlencode({
            'configuration_id': self.profile.ConfigurationId or '',
            'instance_id': self.instance_id,
        })
        return urlunsplit((scheme, endpoint.netloc, '/ws/accounts/credential-events/', query, ''))

    def _event_stream_headers(self):
        url = self._event_stream_url()
        prepared = requests.Request('GET', url, headers={
            'Accept': 'application/json',
            'X-JMS-ORG': self.profile.OrgId,
            'X-Source': self.profile.Source,
            'X-JMS-Client-Version': __version__,
            'X-JMS-Protocol-Version': str(PROTOCOL_VERSION),
            'X-JMS-Config-Schema-Version': (
                str(CONFIG_SCHEMA_VERSION) if self.profile.Source == 'jms-pam-agent' else '0'
            ),
            'Date': formatdate(usegmt=True),
        }).prepare()
        self.auth(prepared)
        return [f'{name}: {value}' for name, value in prepared.headers.items()]
