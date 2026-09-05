import base64
import hashlib
import hmac
import json
import os
import socket
import threading
from dataclasses import dataclass
from email.utils import formatdate

import requests
from requests.auth import AuthBase

DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000002'
CLIENT_PATH = '/api/v1/accounts/credential-client'
SIGNATURE_HEADERS = ('(request-target)', 'accept', 'date', 'x-jms-org')


class HTTPSignatureAuth(AuthBase):
    def __init__(self, key_id, secret):
        self.key_id = key_id
        self.secret = secret.encode('ascii')

    def __call__(self, request):
        values = []
        for header in SIGNATURE_HEADERS:
            value = (
                f'{request.method.lower()} {request.path_url}'
                if header == '(request-target)'
                else request.headers[header]
            )
            values.append(f'{header}: {value}')
        digest = base64.b64encode(hmac.new(
            self.secret, '\n'.join(values).encode('ascii'), hashlib.sha256,
        ).digest()).decode('ascii')
        request.headers['Authorization'] = (
            f'Signature keyId="{self.key_id}",algorithm="hmac-sha256",'
            f'signature="{digest}",headers="{" ".join(SIGNATURE_HEADERS)}"'
        )
        return request


@dataclass(frozen=True)
class Credential:
    key: str
    revision: int
    asset: dict
    account: dict

    @property
    def account_id(self):
        return self.account['id']

    @property
    def username(self):
        return self.account['username']

    @property
    def secret(self):
        return self.account['secret']


class SignedClient:
    def __init__(
        self, endpoint, key_id, key_secret, org_id=DEFAULT_ORG_ID,
        source='jms-pam', timeout=10,
    ):
        self.endpoint = endpoint.rstrip('/')
        self.org_id = org_id
        self.source = source
        self.timeout = timeout
        self.session = requests.Session()
        self.auth = HTTPSignatureAuth(
            key_id=key_id,
            secret=key_secret,
        )

    def request(self, method, path, params=None, data=None):
        response = self.session.request(
            method,
            f'{self.endpoint}{path}',
            params=params,
            json=data,
            headers={
                'Accept': 'application/json',
                'X-JMS-ORG': self.org_id,
                'X-Source': self.source,
                'Date': formatdate(usegmt=True),
            },
            auth=self.auth,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                detail = response.json().get('detail')
            except (AttributeError, ValueError):
                detail = None
            if detail:
                error.args = (f'{error}: {detail}',)
            raise
        return response.json()


class CredentialAPIClient(SignedClient):
    def __init__(self, *args, instance_id='', configuration_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance_id = instance_id
        self.configuration_id = configuration_id

    def get_credential(self, key):
        params = {'key': key}
        if self.instance_id:
            params['instance_id'] = self.instance_id
        if self.configuration_id:
            params['configuration_id'] = self.configuration_id
        return self.request('GET', f'{CLIENT_PATH}/credential/', params=params)

    def confirm(self, item):
        data = dict(item)
        if self.instance_id:
            data['instance_id'] = self.instance_id
        if self.configuration_id:
            data['configuration_id'] = self.configuration_id
        return self.request('POST', f'{CLIENT_PATH}/confirm/', data=data)

    def heartbeat(self, credentials):
        data = {'credentials': credentials}
        if self.instance_id:
            data['instance_id'] = self.instance_id
        if self.configuration_id:
            data['configuration_id'] = self.configuration_id
        return self.request('POST', f'{CLIENT_PATH}/heartbeat/', data=data)


class JumpServerPAMClient:
    def __init__(
        self, endpoint, app_id, app_secret, org_id=DEFAULT_ORG_ID,
        instance_id=None, heartbeat_interval=30,
        configuration_id=None,
    ):
        self.instance_id = instance_id or os.getenv('JMS_PAM_INSTANCE_ID') or socket.gethostname()
        self.heartbeat_interval = heartbeat_interval
        self.http = CredentialAPIClient(
            endpoint, app_id, app_secret, org_id, instance_id=self.instance_id,
            configuration_id=configuration_id,
        )
        self._applied = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._heartbeat_thread = None
        self.last_heartbeat_error = None

    @classmethod
    def from_config(cls, path):
        with open(path, encoding='utf-8') as stream:
            config = json.load(stream)
        return cls(**{key: config[key] for key in (
            'endpoint', 'app_id', 'app_secret', 'org_id', 'configuration_id',
            'instance_id', 'heartbeat_interval',
        ) if key in config})

    def get_credential(self, key):
        data = self.http.get_credential(key)
        self._start_heartbeat()
        return Credential(**data)

    def confirm_applied(self, credential=None, *, key=None, revision=None, account_id=None):
        if credential is not None:
            key = credential.key
            revision = credential.revision
            account_id = credential.account_id
        if not all((key, revision, account_id)):
            raise ValueError('credential or key, revision and account_id are required')
        self.http.confirm({
            'key': key,
            'revision': revision,
            'account_id': account_id,
        })
        with self._lock:
            self._applied[key] = {
                'key': key,
                'revision': revision,
                'account_id': account_id,
            }

    def heartbeat(self):
        with self._lock:
            credentials = list(self._applied.values())
        return self.http.heartbeat(credentials)

    def _start_heartbeat(self):
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name='jms-pam-heartbeat',
            daemon=True,
        )
        self._heartbeat_thread.start()

    def _heartbeat_loop(self):
        while not self._stop.wait(self.heartbeat_interval):
            try:
                self.heartbeat()
                self.last_heartbeat_error = None
            except requests.RequestException as error:
                self.last_heartbeat_error = error

    def close(self):
        self._stop.set()
        self.http.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


JumpServerPAM = JumpServerPAMClient
