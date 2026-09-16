import ipaddress
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


_JINJA_DELIMITER_RE = re.compile(r'\{\{|\}\}|\{%|%\}|\{#|#\}')
_HOST_LABEL_RE = re.compile(r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$')


def validate_asset_address(value):
    if not isinstance(value, str):
        raise ValidationError(_('Invalid address'))

    if value != value.strip():
        raise ValidationError(
            _('The address cannot contain leading or trailing whitespace')
        )

    if _JINJA_DELIMITER_RE.search(value):
        raise ValidationError(
            _('The address cannot contain template syntax')
        )

    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValidationError(
            _('The address cannot contain control characters')
        )


def validate_ip_or_hostname(value):
    try:
        ipaddress.ip_address(value)
        return
    except ValueError:
        pass

    # Do not accept malformed IPv4 addresses as numeric hostnames.
    if re.fullmatch(r'[0-9.]+', value):
        raise ValidationError(_('Enter a valid IP address or hostname'))

    try:
        hostname = value.encode('idna').decode('ascii')
    except UnicodeError:
        raise ValidationError(_('Enter a valid IP address or hostname'))

    labels = hostname.split('.')
    if (
            len(hostname) > 253
            or hostname.endswith('.')
            or not all(_HOST_LABEL_RE.fullmatch(label) for label in labels)
    ):
        raise ValidationError(_('Enter a valid IP address or hostname'))
