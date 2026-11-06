from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError

from common.validators import validate_mcp_resource_url


def get_mcp_authorization_server(site_url=None):
    """Use the configured public site origin for Agent OAuth and components."""
    value = settings.SITE_URL if site_url is None else site_url
    try:
        uri = urlsplit(value)
        origin = f'{uri.scheme}://{uri.netloc}'
        if (uri.query or uri.fragment or any(char in value for char in '\\?#')
                or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValueError
        validate_mcp_resource_url(origin + '/mcp')
    except (ValueError, TypeError, UnicodeError, ValidationError) as exc:
        raise ImproperlyConfigured('Agent MCP requires SITE_URL to be a public HTTP or HTTPS URL.') from exc
    return origin
