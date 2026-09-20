import base64
import copy
import hashlib
import hmac
from email.utils import formatdate

import requests
from requests.auth import AuthBase

from .. import CONFIG_SCHEMA_VERSION, PROTOCOL_VERSION, __version__
from .abstract_model import AbstractModel
from .credential import Credential
from .exception import JumpServerPAMSDKException
from .profile.client_profile import ClientProfile

SIGNATURE_HEADERS = (
    '(request-target)', 'accept', 'date', 'x-jms-org',
    'x-jms-client-version', 'x-jms-protocol-version', 'x-jms-config-schema-version',
)


class HTTPSignatureAuth(AuthBase):
    def __init__(self, key_id, secret):
        self.key_id = key_id
        self.secret = secret.encode('ascii')

    def __call__(self, request):
        values = []
        for header in SIGNATURE_HEADERS:
            value = (
                f'{request.method.lower()} {request.path_url}'
                if header == '(request-target)' else request.headers[header]
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


class AbstractClient:
    def __init__(self, cred, instance_id, profile):
        if not isinstance(cred, Credential):
            raise TypeError('cred must be a Credential')
        if not isinstance(profile, ClientProfile):
            raise TypeError('profile must be a ClientProfile')
        if (
            not isinstance(instance_id, str) or not instance_id.strip()
            or instance_id != instance_id.strip() or len(instance_id) > 128
        ):
            raise ValueError(
                'instance_id must be a stable, unique ID with 1-128 characters '
                'and no surrounding whitespace'
            )
        self.credential = cred
        self.instance_id = instance_id
        self.profile = profile
        self.session = requests.Session()
        self.auth = HTTPSignatureAuth(cred.AppId, cred.AppSecret)

    @property
    def source(self):
        return self.profile.Source

    def _request(self, method, path, request, response_type, query=False):
        if not isinstance(request, AbstractModel):
            raise TypeError('request must be an AbstractModel')
        request._validate()
        data = request._serialize()
        data['instance_id'] = self.instance_id
        if self.profile.ConfigurationId:
            data['configuration_id'] = self.profile.ConfigurationId
        response = None
        try:
            response = self.session.request(
                method,
                f'{self.profile.Endpoint}{path}',
                params=data if query else None,
                json=None if query else data,
                headers={
                    'Accept': 'application/json',
                    'X-JMS-ORG': self.profile.OrgId,
                    'X-Source': self.profile.Source,
                    'X-JMS-Client-Version': __version__,
                    'X-JMS-Protocol-Version': str(PROTOCOL_VERSION),
                    'X-JMS-Config-Schema-Version': (
                        str(CONFIG_SCHEMA_VERSION) if self.profile.Source == 'jms-pam-agent' else '0'
                    ),
                    'Date': formatdate(usegmt=True),
                },
                auth=self.auth,
                timeout=self.profile.Timeout,
            )
        except requests.RequestException as error:
            raise JumpServerPAMSDKException(
                'NetworkError', str(error), original_error=error,
            ) from error

        try:
            payload = response.json()
        except (TypeError, ValueError) as error:
            raise JumpServerPAMSDKException(
                'ResponseError', 'The server returned invalid JSON',
                status_code=response.status_code, original_error=error,
            ) from error
        if not isinstance(payload, dict):
            raise JumpServerPAMSDKException(
                'ResponseError', 'The server response must be a JSON object',
                status_code=response.status_code,
            )
        if not 200 <= response.status_code < 300:
            original_error = requests.HTTPError(
                f'{response.status_code} {response.reason}', response=response,
            )
            raise JumpServerPAMSDKException(
                payload.get('code') or 'HTTPError',
                payload.get('detail') or response.reason or 'HTTP request failed',
                status_code=response.status_code,
                detail=payload.get('detail'),
                request_id=payload.get('request_id'),
                original_error=original_error,
            ) from original_error
        try:
            return response_type()._deserialize(payload)._validate()
        except (KeyError, TypeError, ValueError) as error:
            raise JumpServerPAMSDKException(
                'ResponseError', 'The server returned an invalid response',
                status_code=response.status_code, original_error=error,
            ) from error

    def clone(self):
        return type(self)(self.credential, self.instance_id, copy.copy(self.profile))

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
