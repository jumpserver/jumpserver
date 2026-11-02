"""VCTK_S REST random generation and attached-signature verification."""
import json
import threading
import time
from http.client import HTTPException
from uuid import uuid4

from django.utils.translation import gettext_lazy as _

from .fisherman import (
    MAX_CERT, MAX_RESPONSE, FishermanClient, SVSError, create_tls_context, decode_base64, parse_service_url,
)


# A P7 proof may include its certificate chain, unlike a raw SM2/RSA signature.
MAX_P7_SIZE = 32768
MAX_MESSAGE_SIZE = 4096
RANDOM_BYTES = 32


class VCTKSClient(FishermanClient):
    """Reuse bounded DNS/TLS transport with the VCTK_S HTTP wire protocol."""

    def __init__(self, url, *, tls_verify='system', tls_ca_cert='', connect_timeout=3, read_timeout=5,
                 username='', password=''):
        self.scheme, self.host, self.port = parse_service_url(url)
        if any(type(value) is not int or not 1 <= value <= limit
               for value, limit in ((connect_timeout, 10), (read_timeout, 20))):
            raise SVSError(_('Invalid certificate service connection parameters'))
        self.tls_context = create_tls_context(self.scheme, tls_verify, tls_ca_cert)
        self.connect_timeout, self.read_timeout = connect_timeout, read_timeout
        for value in (username, password):
            if (not isinstance(value, str) or len(value) > 256
                    or any(ord(char) < 32 or ord(char) >= 127 for char in value)):
                raise SVSError(_('Invalid VCTK_S business authorization credentials.'))
        if username and not password:
            raise SVSError(_('VCTK_S business authorization requires a password.'))
        self.username, self.password = username, password

    @staticmethod
    def _decode_response(data):
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        try:
            result = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
            if (type(result) is not dict or not {'code', 'message', 'data'} <= result.keys()
                    or type(result['code']) not in (int, str)
                    or type(result['message']) is not str
                    or type(result['data']) is not dict):
                raise ValueError
            if result['code'] not in (0, '0'):
                raise ValueError
            return result['data']
        except (ValueError, UnicodeError, RecursionError):
            raise SVSError(_('VCTK_S rejected the operation or returned an invalid response.')) from None

    def _request(self, endpoint, params):
        fields = {'generateRandom': {'randomlength'}, 'attachverifysign': {'digestalg', 'signdata'}}
        if type(params) is not dict or fields.get(endpoint) != params.keys():
            raise SVSError(_('Invalid VCTK_S operation'))
        body = json.dumps(params, ensure_ascii=True).encode('utf-8')
        if len(body) > MAX_RESPONSE:
            raise SVSError(_('Certificate service request is too large'))
        headers = {
            'Content-Type': 'application/json;charset=UTF-8', 'messagetype': 'json',
            'serialnumber': uuid4().hex, 'Accept': 'application/json', 'Connection': 'close',
        }
        if self.username:
            headers.update(une=self.username, pwd=self.password)
        connection = timer = None
        try:
            connection = self._connect()
            sock = connection.sock
            sock.settimeout(self.read_timeout)
            deadline = time.monotonic() + self.read_timeout
            timer = threading.Timer(self.read_timeout, self._abort_response, args=(sock,))
            timer.daemon = True
            timer.start()
            connection.request('POST', '/api/v1/' + endpoint, body=body, headers=headers)
            with connection.getresponse() as response:
                if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
                    raise SVSError(_('Certificate service returned an unexpected HTTP response'))
                data = response.read(MAX_RESPONSE + 1)
                if (len(data) > MAX_RESPONSE or response.length not in (None, 0)
                        or time.monotonic() >= deadline):
                    raise SVSError(_('Invalid or timed out certificate service response'))
            return self._decode_response(data)
        except (OSError, HTTPException):
            raise SVSError(_('Certificate service connection failed or timed out')) from None
        finally:
            if timer is not None:
                timer.cancel()
            if connection is not None:
                try:
                    connection.close()
                except (OSError, HTTPException):
                    raise SVSError(_('Certificate service connection failed or timed out')) from None

    def generate_random(self):
        # The manual uses a string field. Reject unexpected decoded lengths
        # instead of guessing units or falling back to locally generated data.
        result = self._request('generateRandom', {'randomlength': str(RANDOM_BYTES)})
        random = decode_base64(result.get('randomResult'), RANDOM_BYTES)
        if len(random) != RANDOM_BYTES:
            raise SVSError(_('VCTK_S returned an unexpected random number length.'))
        return random

    def verify_signed_data(self, signature, digest_algorithm):
        """Verify an attached P7 and return its authenticated content and signer."""
        decode_base64(signature, MAX_P7_SIZE)
        if digest_algorithm not in ('sm3', 'sha256'):
            raise SVSError(_('Invalid VCTK_S signing algorithm.'))
        result = self._request('attachverifysign', {
            'digestalg': digest_algorithm, 'signdata': signature,
        })
        if (type(result.get('digestalg')) is not str
                or result['digestalg'].lower() != digest_algorithm
                or type(result.get('certinfo')) is not dict):
            raise SVSError(_('VCTK_S returned an invalid verification result.'))
        return {
            'plain': decode_base64(result.get('plain'), MAX_MESSAGE_SIZE),
            'certificate': decode_base64(result['certinfo'].get('dscert'), MAX_CERT),
        }
