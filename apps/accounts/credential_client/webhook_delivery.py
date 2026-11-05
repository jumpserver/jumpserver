import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlsplit

from django.conf import settings

from accounts.webhooks import (
    BLOCKED_METADATA_ADDRESSES, MAX_TEMPLATE_BYTES, WebhookValidationError,
    validate_webhook_headers, validate_webhook_url,
)


class WebhookRequestError(Exception):
    def __init__(self, reason, retryable=True):
        super().__init__(reason)
        self.reason = reason
        self.retryable = retryable


def _resolve_target(url):
    try:
        url = validate_webhook_url(url, resolve=False)
    except WebhookValidationError:
        raise WebhookRequestError('Invalid webhook URL.', retryable=False)
    try:
        parsed = urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    except (TypeError, ValueError):
        raise WebhookRequestError('Invalid webhook URL.', retryable=False)
    if (
        parsed.scheme not in ('http', 'https') or not parsed.hostname
        or parsed.username is not None or parsed.password is not None or parsed.fragment
    ):
        raise WebhookRequestError('Invalid webhook URL.', retryable=False)
    try:
        infos = socket.getaddrinfo(
            parsed.hostname, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM,
        )
    except OSError:
        raise WebhookRequestError('Webhook host could not be resolved.')
    addresses = []
    for info in infos:
        try:
            address = ipaddress.ip_address(info[4][0])
        except ValueError:
            raise WebhookRequestError('Webhook host could not be resolved.')
        if getattr(address, 'ipv4_mapped', None):
            address = address.ipv4_mapped
        if (
            address in BLOCKED_METADATA_ADDRESSES or address.is_loopback
            or address.is_link_local or address.is_multicast
            or address.is_reserved or address.is_unspecified
        ):
            raise WebhookRequestError('Webhook target address is not allowed.', retryable=False)
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise WebhookRequestError('Webhook host could not be resolved.')
    return parsed, addresses[0], port


def send_webhook(method, url, headers, body, delivery_id=None, event_id=None):
    parsed, address, port = _resolve_target(url)
    method = str(method).upper()
    if method not in ('POST', 'PUT', 'PATCH'):
        raise WebhookRequestError('Webhook method is not allowed.', retryable=False)
    try:
        headers = dict(validate_webhook_headers(headers or {}))
    except WebhookValidationError:
        raise WebhookRequestError('Webhook header is not allowed.', retryable=False)
    if not any(name.lower() == 'content-type' for name in headers):
        headers['Content-Type'] = 'application/json'
    if delivery_id:
        headers['X-JMS-Delivery-ID'] = str(delivery_id)
    if event_id:
        headers['X-JMS-Event-ID'] = str(event_id)

    hostname = parsed.hostname.encode('idna').decode('ascii')
    default_port = 443 if parsed.scheme == 'https' else 80
    host_header = f'[{hostname}]' if ':' in hostname else hostname
    if port != default_port:
        host_header = f'{host_header}:{port}'
    headers['Host'] = host_header
    path = parsed.path or '/'
    if parsed.query:
        path = f'{path}?{parsed.query}'
    try:
        content = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
    except (TypeError, ValueError):
        raise WebhookRequestError('Webhook body is not valid JSON.', retryable=False)
    if len(content) > MAX_TEMPLATE_BYTES:
        raise WebhookRequestError('Webhook body is too large.', retryable=False)
    if parsed.scheme == 'https':
        context = ssl.create_default_context()
        if not settings.VERIFY_EXTERNAL_SSL:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        connection = http.client.HTTPSConnection(hostname, port, timeout=5, context=context)
    else:
        connection = http.client.HTTPConnection(hostname, port, timeout=5)

    def create_connection(_target, timeout=None, source_address=None):
        sock = socket.create_connection(
            (str(address), port), timeout=3, source_address=source_address,
        )
        sock.settimeout(5)
        return sock

    connection._create_connection = create_connection
    try:
        connection.request(method, path, body=content, headers=headers)
        response = connection.getresponse()
        status = response.status
        response.close()
        return status
    except (TimeoutError, socket.timeout):
        raise WebhookRequestError('Webhook request timed out.')
    except ValueError:
        raise WebhookRequestError('Webhook request is invalid.', retryable=False)
    except (OSError, http.client.HTTPException):
        raise WebhookRequestError('Webhook request failed.')
    finally:
        connection.close()
