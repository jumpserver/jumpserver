import ipaddress
import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def normalize_web_origin(value):
    message = _('Enter an HTTP/HTTPS origin without a path, credentials or wildcard.')
    if not isinstance(value, str) or len(value) > 512 or re.search(r'[\s\\%*?#]', value):
        raise ValidationError(message)
    try:
        url = urlsplit(value)
        host, port = url.hostname, url.port
        if url.scheme not in ('http', 'https') or not host or url.username is not None or url.password is not None:
            raise ValueError()
        if url.path not in ('', '/') or not host.isascii() or host.endswith('.'):
            raise ValueError()
        if ':' in host:
            host = '[' + ipaddress.IPv6Address(host).compressed + ']'
        elif not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)*', host):
            raise ValueError()
        if port == 0:
            raise ValueError()
        suffix = f':{port}' if port and port != (443 if url.scheme == 'https' else 80) else ''
        return f'{url.scheme}://{host}{suffix}'
    except (ValueError, TypeError):
        raise ValidationError(message)


def validate_web_script(value):
    if not isinstance(value, list) or len(value) > 128:
        raise ValidationError(_('Enter at most 128 script steps.'))
    numbers = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError(_('Invalid script step.'))
        number = item.get('step')
        if type(number) is not int or number < 1 or number in numbers:
            raise ValidationError(_('Script step numbers must be unique positive integers.'))
        numbers.add(number)
        if item.get('command') not in ('open', 'type', 'click', 'button', 'sleep', 'code', 'select_frame', 'check', 'interactive', 'success'):
            raise ValidationError(_('Unsupported script command.'))
        for field, limit in (('target', 1024), ('value', 4096)):
            if item.get(field) is not None and (not isinstance(item[field], str) or len(item[field]) > limit):
                raise ValidationError(_('Invalid script step.'))
        if item.get('origin'):
            normalize_web_origin(item['origin'])
        if 'timeout' in item and (type(item['timeout']) is not int or not 1 <= item['timeout'] <= 180):
            raise ValidationError(_('Step timeout must be between 1 and 180 seconds.'))
    if value:
        last = max(numbers)
        if any(item['command'] == 'success' and item['step'] != last for item in value):
            raise ValidationError(_('The success command must be the last step.'))
