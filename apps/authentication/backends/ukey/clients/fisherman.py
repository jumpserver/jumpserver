"""Fisherman signature verification WEB V2.0.0 client and SM2 certificate helpers."""
import base64
import binascii
import ipaddress
import json
import re
import socket
import ssl
import threading
import time
import uuid
from concurrent.futures import Future
from datetime import datetime, timezone
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from urllib.parse import urlsplit

from asn1crypto import keys, pem, x509
from django.core.exceptions import ValidationError
from django.core.validators import DomainNameValidator
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger


# Keep the existing logger name when relocating the protocol client.
logger = get_logger('authentication.backends.ukey.svs')

MAX_RESPONSE = 65536
MAX_CERT = 16384
# Matches the 4096-character Base64 limit on login and binding inputs.
MAX_SIGNATURE = 3072
MAX_TLS_CA = 65536
SM2_OID = '1.2.156.10197.1.301'

# WEB interface manual, section 5. Keep the vendor's identifiers, including typos.
RESPONSE_CODES = {
    0x00000000: ('GM_SUCCESS', _('Success')),
    0x04000000: ('GM_ERROR_BASE', _('Unexpected error')),
    0x04000001: ('GM_ERROR_CERT_ID', _('Invalid certificate identifier')),
    0x04000002: ('GM_ERROR_CERT_INFO_TYPE', _('Invalid certificate information type')),
    0x04000003: ('GM_ERROR_SERVER_CONNECT', _('Service connection failed')),
    0x04000004: ('GM_ERROR_SIGN_METHOD', _('Invalid signature method')),
    0x04000005: ('GM_ERROR_KEY_INDEX', _('Invalid key index')),
    0x04000006: ('GM_ERROR_KEY_VALUE', _('Invalid key value')),
    0x04000007: ('GM_ERROR_CERT', _('Invalid or missing certificate')),
    0x04000008: ('GM_ERROR_CERT_DECODE', _('Certificate parsing failed')),
    0x04000009: ('GM_ERROR_CERT_INVALID_AF', _('Certificate has expired')),
    0x0400000A: ('GM_ERROR_CERT_INVALID_BF', _('Certificate is not yet valid')),
    0x0400000B: ('GM_ERROR_CERT_REMOVERD', _('Certificate has been revoked')),
    0x0400000C: ('GM_INVALID_SIGNATURE', _('Invalid signature')),
    0x0400000D: ('GM_INVALID_DATA_FORMAT', _('Invalid data format')),
    0x0400000E: ('GM_SYSTEM_FAILURE', _('System error')),
    0x0400000F: ('GM_ERROR_PARA', _('Invalid parameters')),
    0x04000010: ('GM_ERROR_SIGN', _('Signing failed')),
    0x04000011: ('GM_ERROR_VERIFY', _('Signature verification failed')),
    0x04000012: ('GM_ERROR_P7', _('P7 signing failed')),
    0x04000013: ('GM_ERROR_KEY', _('Key generation failed')),
    0x04000014: ('GM_ERROR_HASH', _('Hash calculation failed')),
    0x04000015: ('GM_ERROR_OCSP_NORESPONSE', _('No OCSP response')),
    0x04000016: ('GM_ERROR_OCSP_MALFORMEDREQUEST', _('Invalid OCSP request')),
    0x04000017: ('GM_ERROR_OCSP_INTERNALERROR', _('OCSP responder internal error')),
    0x04000018: ('GM_ERROR_OCSP_TRYLATER', _('OCSP service is temporarily unavailable. Try again later')),
    0x04000019: ('GM_ERROR_OCSP_SIGREQUIRED', _('OCSP request is not signed')),
    0x0400001A: ('GM_ERROR_OCSP_UNAUTHORIZED', _('OCSP request is not authorized')),
    0x0400001B: ('GM_ERROR_CA_UNFOUND', _('Root CA certificate not found')),
    0x0400001C: ('GM_ERROR_CA_VERIFY', _('Root CA signature verification failed')),
    0x0400001D: ('GM_ERROR_CRL_UNFOUND', _('CRL verification: revoked')),
}

# System DNS calls cannot be cancelled. Bound outstanding lookups per process,
# including timed-out calls, without keeping an unbounded executor queue.
_DNS_SLOTS = threading.BoundedSemaphore(4)


class SVSError(ValueError):
    """Safe, deliberately payload-free error for the calling application."""

    def __init__(self, message, *, cause=None, resp_value=None):
        source = cause if cause is not None else self
        self.exception_type = getattr(source, 'exception_type', type(source).__name__)
        self._fisherman_logged = getattr(cause, '_fisherman_logged', False)
        self.resp_value = None
        self.error_name = ''
        if resp_value is not None:
            code = _parse_response_code(resp_value)
            self.resp_value = format(code, '#010X').replace('X', 'x', 1) if code is not None else '<invalid>'
            if code is None or code == 0:
                # Non-canonical zero strings are not accepted as success by the decoder.
                message = _('Invalid certificate service response')
            else:
                self.error_name, description = RESPONSE_CODES.get(code, ('', _('Unknown error code')))
                if self.error_name:
                    template = _('Fisherman service error: %(message)s (%(name)s, %(code)s).')
                else:
                    template = _('Fisherman service error: %(message)s (%(code)s).')
                message = template % {
                    'message': description, 'name': self.error_name, 'code': self.resp_value,
                }
        super().__init__(message)


def _parse_response_code(value):
    # Vendor responses are untrusted. Accept only bounded numeric codes, never
    # free-form error text or echoed request data. Do not change success handling.
    if (type(value) is str and len(value) <= 21
            and re.fullmatch(r'[+-]?(?:[0-9]{1,20}|0[xX][0-9a-fA-F]{1,16})', value)):
        value = int(value, 16 if 'x' in value.lower() else 10)
    if type(value) is int and value.bit_length() <= 64:
        return value
    return None


def log_failure(exc, operation, stage, **details):
    """Log once per failure; details must contain only locally controlled metadata."""
    if getattr(exc, '_fisherman_logged', False):
        return
    # Only SVSError messages are deliberately payload-free. Library/vendor errors
    # may contain certificates or credentials: log their type, never their text/traceback.
    reason = str(exc) if isinstance(exc, SVSError) else '-'
    if isinstance(exc, SVSError) and exc.resp_value is not None:
        details['respValue'] = exc.resp_value
        details['errorName'] = exc.error_name
    logger.error(
        'Fisherman failure: operation=%s stage=%s exception=%s reason=%s details=%s',
        operation, stage, getattr(exc, 'exception_type', type(exc).__name__), reason, details,
    )
    exc._fisherman_logged = True


class SM2PublicKeyInfo(keys.PublicKeyInfo):
    def _public_key_spec(self):
        if self['algorithm']['algorithm'].dotted == SM2_OID:
            return keys.ECPointBitString, None
        return super()._public_key_spec()

    _spec_callbacks = {'public_key': _public_key_spec}


class CertificateBody(x509.TbsCertificate):
    _fields = [(name, SM2PublicKeyInfo if name == 'subject_public_key_info' else spec, *options)
               for name, spec, *options in x509.TbsCertificate._fields]


class Certificate(x509.Certificate):
    _fields = [('tbs_certificate', CertificateBody), *x509.Certificate._fields[1:]]


def strict_der(cls, data):
    """Strict parsing for uploaded HTTPS trust certificates, not UKey proofs."""
    stage = 'load'
    try:
        value = cls.load(data, strict=True)
        # Force lazy parsing, reject trailing members as well as trailing bytes.
        stage = 'fields'
        if len(value) != len(cls._fields):
            # Optional members may legitimately be absent.
            required = sum(not f[2].get('optional', False) if len(f) > 2 else 1
                           for f in cls._fields)
            if not required <= len(value) <= len(cls._fields):
                raise ValueError
        stage = 'native'
        value.native
        stage = 'canonical'
        if value.dump(force=True) != data:
            raise ValueError
        return value
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        # ASN.1 exception messages may contain input data. Never log them or a traceback.
        log_failure(
            exc, 'parse_der', stage,
            schema=cls.__name__, decoded_bytes=len(data) if isinstance(data, bytes) else 0,
        )
        raise SVSError(_('Invalid DER data'), cause=exc) from None


def decode_base64(value, max_size):
    if not isinstance(value, str) or len(value) > 4 * ((max_size + 2) // 3):
        raise SVSError(_('Invalid encoded data'))
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SVSError(_('Invalid encoded data'), cause=exc) from None
    if not data or len(data) > max_size:
        raise SVSError(_('Invalid encoded data'))
    return data


def load_certificate(data):
    """Read a service-verified certificate for binding, without re-encoding it."""
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_CERT:
        raise SVSError(_('Invalid certificate'))
    certificate = Certificate.load(data, strict=True)
    if len(certificate) != len(Certificate._fields):
        raise SVSError(_('Invalid certificate'))
    return certificate


def _validate_service_ip(host):
    # Private service networks are allowed, but not local/metadata endpoints.
    try:
        address = ipaddress.ip_address(host)
        if address.is_unspecified or address.is_multicast or address.is_link_local:
            raise ValueError
        if address.is_loopback or address.is_reserved:
            raise ValueError
    except ValueError:
        raise SVSError(_('This address is not allowed. Use an address on a trusted service network.')) from None
    return str(address)


def parse_service_url(value):
    """Accept a service origin only; API paths are owned by this client."""
    error_message = _(
        'Enter a valid HTTP or HTTPS service URL without credentials, an API path, query parameters or a fragment.'
    )
    try:
        if (not isinstance(value, str) or not value or len(value) > 2048
                or any(char.isspace() or ord(char) < 32 for char in value)):
            raise ValueError
        parsed = urlsplit(value)
        if (parsed.scheme not in ('http', 'https') or not parsed.netloc
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ('', '/') or '?' in value or '#' in value
                or '\\' in value or parsed.netloc.endswith(':')):
            raise ValueError
        host = parsed.hostname
        if not host or '%' in host:
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            host = host.encode('idna').decode('ascii').lower()
            DomainNameValidator(accept_idna=False)(host)
            if len(host) > 253:
                raise ValueError
        else:
            host = _validate_service_ip(host)
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == 'https' else 80)
        if not 1 <= port <= 65535:
            raise ValueError
        return parsed.scheme, host, port
    except SVSError:
        raise
    except (ValueError, TypeError, UnicodeError, ValidationError):
        raise SVSError(error_message) from None


def create_tls_context(scheme, verify, ca_cert):
    if verify not in ('system', 'custom', 'insecure'):
        raise SVSError(_('Invalid HTTPS certificate verification mode'))
    if scheme != 'https':
        return None
    if verify == 'insecure':
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    if verify == 'system':
        return ssl.create_default_context()
    try:
        if not isinstance(ca_cert, str) or not 1 <= len(ca_cert) <= MAX_TLS_CA:
            raise ValueError
        ca_cert.encode('ascii')
        # Accept only CA certificate PEM blocks, never private keys or other content.
        pattern = r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----'
        blocks = re.findall(pattern, ca_cert, re.DOTALL)
        if not blocks or re.sub(pattern, '', ca_cert, flags=re.DOTALL).strip():
            raise ValueError
        for block in blocks:
            der = pem.unarmor(block.encode('ascii'))[2]
            if not strict_der(Certificate, der).ca:
                raise ValueError
        # Passing cadata loads only these CAs, without also loading system roots.
        return ssl.create_default_context(cadata=ca_cert)
    except (ValueError, TypeError, UnicodeError, OSError) as exc:
        raise SVSError(_(
            'Upload a valid PEM CA certificate for the HTTPS service (maximum 64 KB), without a private key.'
        ), cause=exc) from None


class FishermanClient:
    """Direct SVS JSON API; scoped TLS settings, no redirects, proxies or retries."""

    def __init__(self, url, *, tls_verify='system', tls_ca_cert='', connect_timeout=3, read_timeout=5):
        stage = 'service_url'
        try:
            self.scheme, self.host, self.port = parse_service_url(url)
            stage = 'timeouts'
            bounds = ((connect_timeout, 10), (read_timeout, 20))
            if any(type(value) is not int or not 1 <= value <= limit for value, limit in bounds):
                raise SVSError(_('Invalid certificate service connection parameters'))
            stage = 'tls_context'
            self.tls_context = create_tls_context(self.scheme, tls_verify, tls_ca_cert)
            self.connect_timeout = connect_timeout
            self.read_timeout = read_timeout
        except Exception as exc:
            log_failure(exc, 'configure', stage)
            raise

    def _connect(self):
        deadline = time.monotonic() + self.connect_timeout
        addresses = self._resolve_hosts(deadline)
        context = self.tls_context
        last_error = None
        for index, host in enumerate(addresses):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sock = None
            try:
                family = socket.AF_INET6 if ':' in host else socket.AF_INET
                sock = socket.socket(family, socket.SOCK_STREAM)
                sock.settimeout(remaining / (len(addresses) - index))
                sock.connect((host, self.port))
                if context is not None:
                    sock.settimeout(max(0.001, deadline - time.monotonic()))
                    # Keep the configured hostname for SNI/certificate validation,
                    # but use only the previously validated IP for the connection.
                    sock = context.wrap_socket(sock, server_hostname=self.host)
                if time.monotonic() >= deadline:
                    raise TimeoutError
                if context is not None:
                    connection = HTTPSConnection(self.host, self.port, timeout=self.read_timeout, context=context)
                else:
                    connection = HTTPConnection(self.host, self.port, timeout=self.read_timeout)
                connection.sock = sock
                connection.auto_open = 0  # Never reconnect with a second, unvalidated DNS lookup.
                return connection
            except OSError as exc:
                last_error = exc
                if sock is not None:
                    sock.close()
        raise SVSError(_('Certificate service connection or TLS verification failed'), cause=last_error)

    def _resolve_hosts(self, deadline):
        try:
            ipaddress.ip_address(self.host)
        except ValueError:
            if not _DNS_SLOTS.acquire(timeout=max(0, deadline - time.monotonic())):
                raise SVSError(_('Signature verification service resolution timed out'))
            result = Future()
            # Do not retain the client or connect in the worker: a late DNS result
            # must never cause a late request.
            host, port = self.host, self.port

            def resolve():
                try:
                    result.set_result(socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM))
                except Exception as exc:
                    result.set_exception(exc)
                finally:
                    _DNS_SLOTS.release()

            try:
                threading.Thread(target=resolve, name='ukey-dns', daemon=True).start()
            except RuntimeError as exc:
                _DNS_SLOTS.release()
                raise SVSError(_('Cannot resolve signature verification service address'), cause=exc) from None
            records = result.result(timeout=max(0, deadline - time.monotonic()))
            # Validate every answer before connecting; keep order, remove duplicates.
            # Never pass the domain to connect for a second lookup.
            addresses = list(dict.fromkeys(_validate_service_ip(record[4][0]) for record in records))
            if not addresses:
                raise SVSError(_('Cannot resolve signature verification service address'))
            return addresses
        return [self.host]

    @staticmethod
    def _abort_response(sock):
        # An absolute deadline also bounds slowly trickled HTTP headers/body.
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    @staticmethod
    def _decode_response(data, endpoint):
        def unique_object(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        try:
            result = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
            if not isinstance(result, dict) or result.get('version') != 'v1':
                raise ValueError
            req_type = result.get('reqType')
            if not isinstance(req_type, str) or req_type.strip() not in (endpoint, 'SignServerJson/' + endpoint):
                raise ValueError
            respond = result.get('respond')
            # Vendor Java examples parse respond as JSON text; also accept the
            # nested object specified by the interface tables.
            if isinstance(respond, str):
                respond = json.loads(respond, object_pairs_hook=unique_object)
            if not isinstance(respond, dict):
                raise ValueError
            code = respond.get('respValue')
            if type(code) not in (int, str):
                raise ValueError
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise SVSError(_('Invalid certificate service response'), cause=exc) from None
        # Never accept false, null, missing codes or other truthy/falsy substitutes.
        if code not in (0, '0'):
            raise SVSError(_('Certificate service rejected the request'), resp_value=code)
        return respond

    def _request(self, endpoint, fields):
        request_id = uuid.uuid4().hex
        connection = timer = None
        started = time.perf_counter()
        stage = 'encode'
        try:
            request_time = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%z')
            path = '/SignServerJson/' + endpoint
            headers = {
                'Accept': 'application/json', 'Content-Type': 'application/json', 'Connection': 'close',
                'SVS-Request-Version': 'v1', 'SVS-Request-Time': request_time,
            }
            body = json.dumps({
                'version': 'v1', 'reqType': endpoint, 'request': fields, 'reqTime': request_time,
            }, ensure_ascii=True).encode('utf-8')
            if len(body) > MAX_RESPONSE:
                raise SVSError(_('Certificate service request is too large'))
            stage = 'connect'
            connection = self._connect()
            sock = connection.sock
            sock.settimeout(self.read_timeout)
            deadline = time.monotonic() + self.read_timeout
            timer = threading.Timer(self.read_timeout, self._abort_response, args=(sock,))
            timer.daemon = True
            timer.start()
            stage = 'send'
            connection.request('POST', path, body=body, headers=headers)
            stage = 'receive'
            with connection.getresponse() as response:
                # No redirect following or compressed response decoding.
                if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
                    raise SVSError(_('Certificate service returned an unexpected HTTP response'))
                data = response.read(MAX_RESPONSE + 1)
                if len(data) > MAX_RESPONSE:
                    raise SVSError(_('Certificate service response is too large'))
                if response.length not in (None, 0):
                    raise SVSError(_('Incomplete certificate service response'))
                if time.monotonic() >= deadline:
                    raise SVSError(_('Certificate service response timed out'))
            stage = 'decode'
            result = self._decode_response(data, endpoint)
            logger.debug(
                'SVS REST request_id=%s operation=%s stage=%s outcome=success elapsed_ms=%.2f',
                request_id, endpoint, stage, (time.perf_counter() - started) * 1000,
            )
            return result
        except Exception as exc:
            log_failure(
                exc, endpoint, stage, request_id=request_id,
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            if isinstance(exc, (OSError, HTTPException)):
                raise SVSError(_('Certificate service connection failed or timed out'), cause=exc) from None
            raise
        finally:
            try:
                if timer is not None:
                    timer.cancel()
                if connection is not None:
                    connection.close()
            except Exception as exc:
                log_failure(exc, endpoint, 'cleanup', request_id=request_id)
                raise

    def generate_random(self):
        result = self._request('GenRandomData', {'len': 32})
        try:
            # The interface returns randomData as text, without specifying Base64.
            # Sign that exact text; the SDK and REST inData encode the same bytes.
            data = result.get('randomData')
            if not isinstance(data, str) or not data or not data.isascii():
                raise SVSError(_('Invalid certificate service response'))
            return data
        except Exception as exc:
            log_failure(exc, 'GenRandomData', 'random_data')
            raise

    def verify_signed_data(self, cert, message, signature):
        """Send the original Base64 certificate/signature and encode only the message bytes."""
        # Match the verified Postman examples: check validity and the CA signature.
        # Level 1 requires trusted CAs at the SVS, but does not request a CRL check.
        try:
            fields = {
                'type': 1,
                'cert': cert,
                'certSN': '',
                'inData': base64.b64encode(message).decode('ascii'),
                'signature': signature,
                'verifyLevel': 1,
            }
        except Exception as exc:
            log_failure(exc, 'VerifySignedData', 'encode')
            raise
        self._request('VerifySignedData', fields)
