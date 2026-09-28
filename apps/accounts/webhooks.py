import ipaddress
import json
import re
import socket
from urllib.parse import urlsplit, urlunsplit

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import ApplicationEvent


MAX_TEMPLATE_BYTES = 64 * 1024
MAX_TEMPLATE_DEPTH = 16
PLACEHOLDER = re.compile(r'{{\s*([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)\s*}}')
HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
HEADER_VALUE_CTL = re.compile(r'[\x00-\x08\x0a-\x1f\x7f]')
BLOCKED_HEADERS = {
    'connection', 'content-length', 'forwarded', 'host', 'keep-alive',
    'proxy-authenticate', 'proxy-authorization', 'te', 'trailer',
    'transfer-encoding', 'upgrade', 'via', 'x-http-method',
    'x-http-method-override', 'x-method-override', 'x-real-ip',
}
BLOCKED_METADATA_ADDRESSES = {
    ipaddress.ip_address('100.100.100.200'),
    ipaddress.ip_address('169.254.169.254'),
    ipaddress.ip_address('fd00:ec2::254'),
}

WEBHOOK_TEMPLATE_VARIABLES = {
    'event.id': (_('Event ID'), '00000000-0000-0000-0000-000000000001'),
    'event.code': (_('Event code'), ApplicationEvent.CREDENTIAL_UPDATED),
    'event.result': (_('Event result'), 'success'),
    'event.occurred_at': (_('Occurred at'), '2026-01-01T00:00:00+00:00'),
    'event.summary': (_('Event summary'), 'Credential revision published.'),
    'application.id': (_('Application ID'), '00000000-0000-0000-0000-000000000002'),
    'application.name': (_('Application name'), 'order-service'),
    'credential.id': (_('Credential ID'), '00000000-0000-0000-0000-000000000003'),
    'credential.name': (_('Credential name'), 'Database credential'),
    'credential.key': (_('Credential key'), 'database-credential'),
    'credential.revision': (_('Credential revision'), 1),
    'configuration.id': (_('Configuration ID'), '00000000-0000-0000-0000-000000000004'),
    'configuration.name': (_('Configuration name'), 'Production SDK'),
    'client.instance_id': (_('Client instance ID'), 'order-service-1'),
    'source': (_('Source'), 'JumpServer'),
    'operator': (_('Operator'), 'JumpServer'),
    'remote_addr': (_('Remote address'), '192.0.2.1'),
    'rotation.id': (_('Rotation ID'), '00000000-0000-0000-0000-000000000005'),
}


class WebhookValidationError(ValueError):
    pass


def webhook_template_variables():
    return [
        {'name': value, 'label': str(label), 'default': example}
        for value, (label, example) in WEBHOOK_TEMPLATE_VARIABLES.items()
    ]


def _blocked_address(value):
    address = ipaddress.ip_address(value)
    if getattr(address, 'ipv4_mapped', None):
        address = address.ipv4_mapped
    return address in BLOCKED_METADATA_ADDRESSES or any((
        address.is_loopback, address.is_link_local, address.is_multicast,
        address.is_reserved, address.is_unspecified,
    ))


def validate_webhook_url(value, resolve=True):
    value = (value or '').strip()
    try:
        URLValidator(schemes=('http', 'https'))(value)
        parsed = urlsplit(value)
        if parsed.username is not None or parsed.password is not None:
            raise WebhookValidationError(_('URL credentials are not allowed.'))
        if parsed.fragment:
            raise WebhookValidationError(_('URL fragments are not allowed.'))
        port = parsed.port
        if port == 0:
            raise WebhookValidationError(_('URL port must be between 1 and 65535.'))
        port = port or (443 if parsed.scheme == 'https' else 80)
        if resolve:
            addresses = {
                item[4][0] for item in socket.getaddrinfo(
                    parsed.hostname, port, type=socket.SOCK_STREAM,
                )
            }
            if not addresses or any(_blocked_address(address) for address in addresses):
                raise WebhookValidationError(_('URL resolves to a forbidden address.'))
    except WebhookValidationError:
        raise
    except (DjangoValidationError, OSError, TypeError, ValueError) as exc:
        raise WebhookValidationError(_('Enter a valid and resolvable HTTP(S) URL.')) from exc
    return value


def mask_webhook_url(value):
    if not value:
        return ''
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    if ':' in host:
        host = f'[{host}]'
    if parsed.port:
        host = f'{host}:{parsed.port}'
    return urlunsplit((parsed.scheme, host, '/***', '', ''))


def validate_webhook_headers(value):
    if not isinstance(value, dict):
        raise WebhookValidationError(_('Request headers must be an object.'))
    if len(value) > 32:
        raise WebhookValidationError(_('No more than 32 request headers are allowed.'))
    names = set()
    for name, content in value.items():
        lower_name = name.lower() if isinstance(name, str) else ''
        if not HEADER_NAME.fullmatch(name or '') or len(name) > 128:
            raise WebhookValidationError(_('Request header name is invalid.'))
        if lower_name in names:
            raise WebhookValidationError(_('Request header names must be unique.'))
        names.add(lower_name)
        if lower_name in BLOCKED_HEADERS or lower_name.startswith(('proxy-', 'x-forwarded-', 'x-jms-')):
            raise WebhookValidationError(_('Request header is reserved by JumpServer.'))
        if not isinstance(content, str) or len(content) > 4096:
            raise WebhookValidationError(_('Request header values must be strings up to 4096 characters.'))
        if HEADER_VALUE_CTL.search(content):
            raise WebhookValidationError(_('Request header values contain invalid control characters.'))
        try:
            content.encode('latin-1')
        except UnicodeEncodeError as exc:
            raise WebhookValidationError(
                _('Request header values must contain only ISO-8859-1 characters.')
            ) from exc
        if '{{' in content or '}}' in content:
            raise WebhookValidationError(_('Request headers cannot contain template variables.'))
    if len(json.dumps(value, ensure_ascii=False).encode()) > 16 * 1024:
        raise WebhookValidationError(_('Request headers are too large.'))
    return value


def _validate_template_node(value, depth=1):
    if depth > MAX_TEMPLATE_DEPTH:
        raise WebhookValidationError(_('Webhook template is too deeply nested.'))
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or '{{' in key or '}}' in key:
                raise WebhookValidationError(_('Webhook template keys must be static strings.'))
            _validate_template_node(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _validate_template_node(child, depth + 1)
    elif isinstance(value, str):
        if '{{{' in value or '}}}' in value:
            raise WebhookValidationError(_('Webhook template contains an invalid expression.'))
        matches = list(PLACEHOLDER.finditer(value))
        remainder = PLACEHOLDER.sub('', value)
        if any(token in remainder for token in ('{{', '}}', '{%', '%}', '{#', '#}')):
            raise WebhookValidationError(_('Webhook template contains an invalid expression.'))
        unknown = [match.group(1) for match in matches if match.group(1) not in WEBHOOK_TEMPLATE_VARIABLES]
        if unknown:
            raise WebhookValidationError(_('Unknown webhook template variable: %s') % unknown[0])


def validate_webhook_template(template):
    if not isinstance(template, dict):
        raise WebhookValidationError(_('Webhook template must be a JSON object.'))
    try:
        size = len(json.dumps(template, ensure_ascii=False, separators=(',', ':')).encode())
    except (TypeError, ValueError) as exc:
        raise WebhookValidationError(_('Webhook template must contain valid JSON values.')) from exc
    if size > MAX_TEMPLATE_BYTES:
        raise WebhookValidationError(_('Webhook template cannot exceed 64 KiB.'))
    _validate_template_node(template)
    return template


def _context_value(context, path):
    value = context
    for part in path.split('.'):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def _string_value(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def render_webhook_template(template, context):
    validate_webhook_template(template)

    def render(value):
        if isinstance(value, dict):
            return {key: render(child) for key, child in value.items()}
        if isinstance(value, list):
            return [render(child) for child in value]
        if not isinstance(value, str):
            return value
        exact = PLACEHOLDER.fullmatch(value)
        if exact:
            return _context_value(context, exact.group(1))
        return PLACEHOLDER.sub(
            lambda match: _string_value(_context_value(context, match.group(1))), value,
        )

    rendered = render(template)
    if len(json.dumps(rendered, ensure_ascii=False, separators=(',', ':')).encode()) > MAX_TEMPLATE_BYTES:
        raise WebhookValidationError(_('Rendered webhook body cannot exceed 64 KiB.'))
    return rendered


def build_webhook_context(event, application=None, code=None):
    if application is None and event.service_id:
        from accounts.models import IntegrationApplication
        application = IntegrationApplication.objects.filter(id=event.service_id).first()
    occurred_at = event.date_created.isoformat() if event.date_created else None
    return {
        'event': {
            'id': str(event.id), 'code': code or event.event,
            'result': event.result, 'occurred_at': occurred_at, 'summary': event.summary,
        },
        'application': {
            'id': str(application.id) if application else (str(event.service_id) if event.service_id else None),
            'name': application.name if application else event.service,
        },
        'credential': {
            'id': str(event.credential_id) if event.credential_id else None,
            'name': event.credential or None, 'key': event.credential_key or None,
            'revision': event.revision,
        },
        'configuration': {
            'id': str(event.configuration_id) if event.configuration_id else None,
            'name': event.configuration or None,
        },
        'client': {'instance_id': event.instance_id or None},
        'source': event.source or None,
        'operator': event.operator or None,
        'remote_addr': str(event.remote_addr) if event.remote_addr else None,
        'rotation': {'id': str(event.rotation_id) if event.rotation_id else None},
    }


def sample_webhook_context(application, code=ApplicationEvent.CREDENTIAL_UPDATED):
    failed = code in (
        ApplicationEvent.CREDENTIAL_CHANGE_FAILED, ApplicationEvent.ROTATION_FAILED,
    )
    now = timezone.now().isoformat()
    return {
        'event': {
            'id': '00000000-0000-0000-0000-000000000001', 'code': code,
            'result': 'failed' if failed else 'success', 'occurred_at': now,
            'summary': str(dict(ApplicationEvent.choices).get(code, code)),
        },
        'application': {'id': str(application.id), 'name': application.name},
        'credential': {
            'id': '00000000-0000-0000-0000-000000000003',
            'name': 'Database credential', 'key': 'database-credential', 'revision': 1,
        },
        'configuration': {
            'id': '00000000-0000-0000-0000-000000000004',
            'name': 'Production SDK',
        },
        'client': {'instance_id': 'order-service-1'},
        'source': 'JumpServer', 'operator': 'JumpServer', 'remote_addr': '192.0.2.1',
        'rotation': {'id': '00000000-0000-0000-0000-000000000005'},
    }
