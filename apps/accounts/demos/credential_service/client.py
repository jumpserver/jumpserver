#!/usr/bin/env python3
"""JumpServer credential service client using only the Python standard library."""

import argparse
import base64
import hashlib
import hmac
import json
import os
import socket
import sys
import uuid
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class Response(NamedTuple):
    status: int
    headers: dict
    data: object


class CredentialServiceError(RuntimeError):
    def __init__(self, status, code, detail):
        self.status = status
        self.code = code
        self.detail = detail
        super().__init__(f'{status} {code}: {detail}')

    @property
    def retryable(self):
        return self.status in (0, 429, 502, 503, 504)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CredentialServiceClient:
    source = 'jms-pam'

    def __init__(self, endpoint, app_id, app_secret, org_id, timeout=35):
        self.endpoint = endpoint.rstrip('/')
        self.app_id = app_id
        self.app_secret = app_secret
        self.org_id = org_id
        self.timeout = timeout
        self.opener = build_opener(_NoRedirect)

    def _sign(self, method, target, headers, signed_headers):
        lines = []
        for name in signed_headers:
            value = (
                f'{method.lower()} {target}'
                if name == '(request-target)'
                else headers[name]
            )
            lines.append(f'{name}: {value}')
        signature = base64.b64encode(hmac.new(
            self.app_secret.encode(), '\n'.join(lines).encode(), hashlib.sha256,
        ).digest()).decode()
        names = ' '.join(signed_headers)
        return (
            f'Signature keyId="{self.app_id}",algorithm="hmac-sha256",'
            f'headers="{names}",signature="{signature}"'
        )

    def build_request(
            self, method, path, payload=None, idempotency_key=None,
            extra_headers=None, date=None, nonce=None,
    ):
        url = self.endpoint + path
        parsed = urlsplit(url)
        target = parsed.path + (f'?{parsed.query}' if parsed.query else '')
        body = None
        headers = {
            'accept': 'application/json',
            'date': date or format_datetime(datetime.now(timezone.utc), usegmt=True),
            'x-jms-org': self.org_id,
            'x-source': self.source,
            'x-jms-nonce': nonce or uuid.uuid4().hex,
        }
        signed_headers = [
            '(request-target)', 'date', 'x-jms-org', 'x-source', 'x-jms-nonce',
        ]
        if payload is not None:
            body = json.dumps(
                payload, ensure_ascii=False, separators=(',', ':'),
            ).encode()
            headers['content-type'] = 'application/json'
            headers['digest'] = 'SHA-256=' + base64.b64encode(
                hashlib.sha256(body).digest(),
            ).decode()
            signed_headers.append('digest')
        if idempotency_key:
            headers['idempotency-key'] = idempotency_key
            signed_headers.append('idempotency-key')
        headers.update({
            key.lower(): value for key, value in (extra_headers or {}).items()
        })
        headers['authorization'] = self._sign(
            method, target, headers, signed_headers,
        )
        return Request(url, data=body, headers=headers, method=method.upper())

    @staticmethod
    def _decode(body):
        if not body:
            return None
        try:
            return json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return body.decode(errors='replace')

    def _send(self, request):
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return Response(
                    response.status, dict(response.headers),
                    self._decode(response.read()),
                )
        except HTTPError as error:
            if error.code == 304:
                return Response(304, dict(error.headers), None)
            data = self._decode(error.read())
            code = data.get('code', 'HTTP_ERROR') if isinstance(data, dict) \
                else 'HTTP_ERROR'
            detail = data.get('detail', data) if isinstance(data, dict) else data
            raise CredentialServiceError(error.code, code, detail) from error
        except (URLError, TimeoutError, socket.timeout) as error:
            raise CredentialServiceError(
                0, 'NETWORK_ERROR', str(getattr(error, 'reason', error)),
            ) from error

    def read_fixed_credential(self, policy_id, etag=None):
        path = (
            '/api/v1/accounts/credential-service/policies/'
            f'{quote(str(policy_id), safe="")}/credential/'
        )
        headers = {'If-None-Match': etag} if etag else None
        return self._send(self.build_request('GET', path, extra_headers=headers))

    def issue_temporary_credential(self, policy_id, idempotency_key=None):
        path = (
            '/api/v1/accounts/credential-service/policies/'
            f'{quote(str(policy_id), safe="")}/credentials/'
        )
        return self._send(self.build_request(
            'POST', path, idempotency_key=idempotency_key,
        ))

    def get_lease(self, lease_id):
        path = (
            '/api/v1/accounts/credential-service/leases/'
            f'{quote(str(lease_id), safe="")}/'
        )
        return self._send(self.build_request('GET', path))

    def renew_lease(self, lease_id, increment=None):
        path = (
            '/api/v1/accounts/credential-service/leases/'
            f'{quote(str(lease_id), safe="")}/renew/'
        )
        payload = {} if increment is None else {'increment': increment}
        return self._send(self.build_request('POST', path, payload=payload))

    def revoke_lease(self, lease_id):
        path = (
            '/api/v1/accounts/credential-service/leases/'
            f'{quote(str(lease_id), safe="")}/'
        )
        return self._send(self.build_request('DELETE', path))


def _client_from_env():
    missing = [
        name for name in ('JMS_URL', 'JMS_APP_ID', 'JMS_APP_SECRET', 'JMS_ORG_ID')
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit('Missing environment variables: ' + ', '.join(missing))
    return CredentialServiceClient(
        os.environ['JMS_URL'], os.environ['JMS_APP_ID'],
        os.environ['JMS_APP_SECRET'], os.environ['JMS_ORG_ID'],
        float(os.environ.get('JMS_TIMEOUT', '35')),
    )


def _self_test():
    client = CredentialServiceClient(
        'https://jumpserver.example', 'app-id', 'app-secret', 'org-id',
    )
    request = client.build_request(
        'POST', '/api/v1/accounts/credential-service/leases/lease-id/renew/',
        payload={'increment': 600}, idempotency_key='request-id',
        date='Wed, 26 Aug 2026 01:02:03 GMT',
        nonce='0123456789abcdef',
    )
    assert request.data == b'{"increment":600}'
    assert request.get_header('Digest') == (
        'SHA-256=kM51QBCQp6pSOoFQhdajLq1FXHQjo3+4vYc8wvImdkU='
    )
    assert request.get_header('Authorization').endswith(
        'signature="5FPV4Gdu5CO9SCedR4WVrWL9uSjF/DrFkv/hGhaD1EA="'
    )
    print('credential service client self-test: OK')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('self-test')
    for command in ('fixed', 'issue'):
        item = subparsers.add_parser(command)
        item.add_argument('policy_id')
    subparsers.choices['fixed'].add_argument('--etag')
    subparsers.choices['issue'].add_argument('--idempotency-key')
    for command in ('lease', 'revoke'):
        item = subparsers.add_parser(command)
        item.add_argument('lease_id')
    renew = subparsers.add_parser('renew')
    renew.add_argument('lease_id')
    renew.add_argument('--increment', type=int)
    args = parser.parse_args()

    if args.command == 'self-test':
        _self_test()
        return

    client = _client_from_env()
    methods = {
        'fixed': lambda: client.read_fixed_credential(args.policy_id, args.etag),
        'issue': lambda: client.issue_temporary_credential(
            args.policy_id, args.idempotency_key,
        ),
        'lease': lambda: client.get_lease(args.lease_id),
        'renew': lambda: client.renew_lease(args.lease_id, args.increment),
        'revoke': lambda: client.revoke_lease(args.lease_id),
    }
    try:
        response = methods[args.command]()
        print(json.dumps({
            'status': response.status,
            'etag': response.headers.get('ETag'),
            'data': response.data,
        }, ensure_ascii=False, indent=2, default=str))
    except CredentialServiceError as error:
        print(json.dumps({
            'status': error.status,
            'code': error.code,
            'detail': error.detail,
            'retryable': error.retryable,
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
