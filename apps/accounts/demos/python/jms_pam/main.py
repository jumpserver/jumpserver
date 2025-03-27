import uuid
from datetime import datetime
from urllib.parse import urlencode

import requests
from httpsig.requests_auth import HTTPSignatureAuth
from requests.exceptions import RequestException

DEFAULT_ORG_ID = '00000000-0000-0000-0000-000000000002'


class RequestParamsError(ValueError):
    def __init__(self, params):
        self.params = params

    def __str__(self):
        msg = "At least one of the following fields must be provided: %s."
        return 'RequestParamsError: (%s)' % msg % ', '.join(self.params)


class SecretRequest(object):
    """
    Validate parameters and their interdependencies.
    Parameters:
        account_id (str): The account ID, must be a valid UUID.
        asset_id (str): The asset ID, must be a valid UUID.
        asset (str): The name of the asset, can be empty.
        account (str): The name of the account, can be empty.

    Validation Logic:
    - When 'account_id' is provided, 'asset', 'asset_id', and 'account' must not be provided.
    - When 'account' is provided, either 'asset' or 'asset_id' must be provided.
    - It is not allowed to provide both 'account_id' and 'asset_id' together.

    Raises:
        ValueError: If the parameters do not meet the requirements, a detailed error message will be raised.
    """

    def __init__(self, asset='', asset_id='', account='', account_id=''):
        self.account_id = account_id
        self.asset_id = asset_id
        self.asset = asset
        self.account = account
        self.method = 'get'
        self._init_check()

    @staticmethod
    def _valid_uuid(value):
        if not value:
            return

        try:
            uuid.UUID(str(value))
        except (ValueError, TypeError):
            raise ValueError('Invalid UUID: %s. Value must be a valid UUID.' % value)

    def _init_check(self):
        for id_value in [self.account_id, self.asset_id]:
            self._valid_uuid(id_value)

        if self.account_id:
            return

        if not self.asset_id and not self.asset:
            raise RequestParamsError(['asset', 'asset_id'])

        if not self.account:
            raise RequestParamsError(['account', 'account_id'])

    @staticmethod
    def get_url():
        return '/api/v1/accounts/service-integrations/account-secret/'

    def get_query(self):
        return {k: getattr(self, k) for k in vars(self) if getattr(self, k)}


class Secret(object):
    def __init__(self, secret='', desc=''):
        self.secret = secret
        self.desc = desc
        self.valid = not desc

    @classmethod
    def from_exception(cls, e):
        return cls(desc=str(e))

    @classmethod
    def from_response(cls, response):
        secret, error = '', ''
        try:
            data = response.json()
            if response.status_code != 200:
                for k, v in data.items():
                    error += '%s: %s; ' % (k, v)
            secret = data.get('secret')
        except Exception as e:
            error = str(e)
        return cls(secret=secret, desc=error)


class JumpServerPAM(object):
    def __init__(self, endpoint, key_id, key_secret, org_id=DEFAULT_ORG_ID):
        self.endpoint = endpoint
        self.key_id = key_id
        self.key_secret = key_secret
        self.org_id = org_id
        self._auth = None

    @property
    def headers(self):
        gmt_form = '%a, %d %b %Y %H:%M:%S GMT'
        return {
            'Accept': 'application/json',
            'X-JMS-ORG': self.org_id,
            'Date': datetime.utcnow().strftime(gmt_form),
            'X-Source': 'jms-pam'
        }

    def _build_url(self, url, query_params=None):
        query_params = query_params or {}
        endpoint = self.endpoint[:-1] if self.endpoint.endswith('/') else self.endpoint
        return '%s%s?%s' % (endpoint, url, urlencode(query_params))

    def _get_auth(self):
        if self._auth is None:
            signature_headers = ['(request-target)', 'accept', 'date']
            self._auth = HTTPSignatureAuth(
                key_id=self.key_id, secret=self.key_secret,
                algorithm='hmac-sha256', headers=signature_headers
            )
        return self._auth

    def send(self, secret_request):
        try:
            url = secret_request.get_url()
            query_params = secret_request.get_query()
            request_method = getattr(requests, secret_request.method)
            response = request_method(
                self._build_url(url, query_params),
                auth=self._get_auth(), headers=self.headers
            )
        except RequestException as e:
            return Secret.from_exception(e)
        return Secret.from_response(response)

    def get_accounts(self):
        pass
