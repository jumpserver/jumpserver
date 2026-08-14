# -*- coding: utf-8 -*-
import time
from urllib.parse import quote

import requests
from requests import exceptions as request_exceptions

from common.utils import get_logger, random_string

logger = get_logger(__name__)

__all__ = ['OpenBaoKVClient']


class OpenBaoAPIError(Exception):
    pass


class OpenBaoKVClient(object):
    max_versions = 20

    def __init__(self, addr=None, token='', mount_point='pam', timeout=10, verify_tls=False):
        self.addr = (addr or 'http://127.0.0.1:8200').rstrip('/')
        self.token = token or ''
        self.mount_point = (mount_point or 'pam').strip('/')
        self.timeout = int(timeout or 10)
        self.verify_tls = self._normalize_bool(verify_tls, default=True)
        self.session = requests.Session()

    def is_active(self):
        path = f'jumpserver-health/{random_string(12)}'
        data = {'secret': 'secret'}
        try:
            self._check_health()
            try:
                self.create(path, data)
            except OpenBaoAPIError as e:
                if getattr(e, 'status_code', None) != 404:
                    raise
                self.enable_secrets_engine()
                self.create(path, data)
            self.get(path)
            self.patch(path, data)
            self.delete(path)
        except Exception as e:
            logger.error(str(e))
            return False, f'OpenBao is not reachable: {e}'
        else:
            return True, ''

    def enable_secrets_engine(self):
        """Create the selected mount as a KV v2 engine when it does not exist."""
        mount_point = quote(self.mount_point, safe='')
        response = self._send(
            'POST', f'/v1/sys/mounts/{mount_point}',
            json={'type': 'kv', 'options': {'version': '2'}},
        )
        if response.status_code not in (200, 204):
            error = self._build_error(response)
            if response.status_code == 403:
                error = OpenBaoAPIError(
                    'The OpenBao token cannot create the requested mount point. '
                    'Grant it create/update access to sys/mounts/*.'
                )
                error.status_code = response.status_code
            raise error

        # OpenBao 2.6 may briefly report that a newly enabled KV engine is being
        # upgraded to v2. Wait for that transition before running the write test.
        deadline = time.monotonic() + self.timeout
        while True:
            response = self._send(
                'POST', f'/v1/{mount_point}/config',
                json={'max_versions': self.max_versions},
            )
            if response.status_code in (200, 204):
                return
            if response.status_code != 400 or time.monotonic() >= deadline:
                raise self._build_error(response)
            time.sleep(0.2)

    def iter_secret_paths(self, prefix=''):
        """Yield all current secret paths below this KV v2 mount."""
        try:
            response = self._request(
                'LIST', self._kv_path('metadata', prefix), expected_statuses=(200,)
            )
        except OpenBaoAPIError as e:
            if getattr(e, 'status_code', None) == 404:
                return
            raise

        for key in response.get('data', {}).get('keys', []):
            path = f'{prefix}{key}'
            if key.endswith('/'):
                yield from self.iter_secret_paths(path)
            else:
                yield path

    def copy_current_secrets_from(self, source):
        """Copy current values and custom metadata from another KV v2 mount."""
        if self.addr == source.addr and self.mount_point == source.mount_point:
            return 0

        copied = 0
        for path in source.iter_secret_paths():
            source_secret = source.get(path)
            if 'data' not in source_secret:
                continue

            target_secret = self.get(path)
            if 'data' in target_secret:
                if target_secret['data'] != source_secret['data']:
                    raise OpenBaoAPIError(
                        f'The target mount already contains different data at {path}'
                    )
                continue

            self.create(path, source_secret['data'])
            metadata = source._request(
                'GET', source._kv_path('metadata', path), expected_statuses=(200,)
            ).get('data', {})
            custom_metadata = metadata.get('custom_metadata') or {}
            if custom_metadata:
                self.update_metadata(path, custom_metadata)
            copied += 1

        # Verify again after copying so a concurrent source update aborts the
        # settings change instead of silently switching to stale data.
        for path in source.iter_secret_paths():
            source_secret = source.get(path)
            if 'data' not in source_secret:
                continue
            target_secret = self.get(path)
            if target_secret.get('data') != source_secret['data']:
                raise OpenBaoAPIError(
                    f'Vault data changed while migrating mount point at {path}'
                )
        return copied

    def get(self, path, version=None):
        params = {'version': version} if version else None
        try:
            response = self._request(
                'GET', self._kv_path('data', path), params=params, expected_statuses=(200,)
            )
        except OpenBaoAPIError as e:
            if getattr(e, 'status_code', None) == 404:
                return {}
            raise
        return response.get('data', {})

    def create(self, path, data: dict):
        self._update_or_create(path=path, data=data)

    def update(self, path, data: dict):
        self._update_or_create(path=path, data=data)

    def patch(self, path, data: dict):
        headers = {'Content-Type': 'application/merge-patch+json'}
        payload = {'data': data}
        try:
            self._request(
                'PATCH', self._kv_path('data', path), json=payload,
                headers=headers, expected_statuses=(200,)
            )
        except OpenBaoAPIError as e:
            if getattr(e, 'status_code', None) != 404:
                raise
            self._update_or_create(path=path, data=data)

    def delete(self, path):
        try:
            self._request('DELETE', self._kv_path('metadata', path), expected_statuses=(200, 204))
        except OpenBaoAPIError as e:
            if getattr(e, 'status_code', None) != 404:
                raise

    def update_metadata(self, path, metadata: dict):
        payload = {
            'max_versions': self.max_versions,
            'custom_metadata': metadata,
        }
        try:
            self._request(
                'POST', self._kv_path('metadata', path), json=payload,
                expected_statuses=(200, 204)
            )
        except OpenBaoAPIError as e:
            if getattr(e, 'status_code', None) == 404:
                logger.error('Update metadata error: {}'.format(e))
                return
            raise

    def _update_or_create(self, path, data: dict):
        payload = {'data': data}
        self._request('POST', self._kv_path('data', path), json=payload, expected_statuses=(200,))

    def _check_health(self):
        response = self._send(
            'GET', '/v1/sys/health',
            params={'standbyok': 'true', 'perfstandbyok': 'true'}
        )
        if response.status_code == 501:
            raise OpenBaoAPIError('OpenBao is not initialized')
        if response.status_code == 503:
            raise OpenBaoAPIError('OpenBao is sealed')
        if response.status_code not in (200, 429, 472, 473):
            raise self._build_error(response)

    def _kv_path(self, scope, path):
        path = quote(str(path).strip('/'), safe='/')
        mount_point = quote(self.mount_point, safe='')
        return f'/v1/{mount_point}/{scope}/{path}'

    def _request(self, method, path, expected_statuses=(200,), **kwargs):
        response = self._send(method, path, **kwargs)
        if response.status_code not in expected_statuses:
            raise self._build_error(response)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def _send(self, method, path, headers=None, **kwargs):
        request_headers = {
            'X-Vault-Request': 'true',
        }
        if self.token:
            request_headers['X-Vault-Token'] = self.token
        if headers:
            request_headers.update(headers)

        url = f'{self.addr}{path}'
        try:
            return self.session.request(
                method, url, headers=request_headers,
                timeout=self.timeout, verify=self.verify_tls, **kwargs
            )
        except request_exceptions.RequestException as e:
            raise OpenBaoAPIError(e)

    @staticmethod
    def _normalize_bool(value, default=True):
        if value is None:
            return default
        if isinstance(value, str):
            return value.lower() not in ('0', 'false', 'no', 'off')
        return bool(value)

    @staticmethod
    def _build_error(response):
        try:
            data = response.json()
        except ValueError:
            data = {}

        errors = data.get('errors') or data.get('error') or response.text
        if isinstance(errors, (list, tuple)):
            errors = '; '.join([str(error) for error in errors])

        error = OpenBaoAPIError(errors or response.reason)
        error.status_code = response.status_code
        return error
