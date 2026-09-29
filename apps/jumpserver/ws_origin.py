import json
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


def normalize_origin(value, allow_path=False):
    if not isinstance(value, str) or not value.isascii() or any(
        char.isspace() or ord(char) < 32 or ord(char) == 127 or char in '\\%*'
        for char in value
    ):
        raise ValueError('Invalid WebSocket origin')
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ('http', 'https') or not parsed.hostname
        or parsed.hostname.startswith('.') or parsed.username is not None
        or parsed.password is not None or parsed.query or parsed.fragment
        or (not allow_path and parsed.path not in ('', '/'))
    ):
        raise ValueError('Invalid WebSocket origin')
    port = parsed.port
    if port == 0:
        raise ValueError('Invalid WebSocket origin port')
    host = parsed.hostname
    if ':' in host:
        host = f'[{host}]'
    default_port = 443 if parsed.scheme == 'https' else 80
    suffix = f':{port}' if port is not None and port != default_port else ''
    return f'{parsed.scheme}://{host}{suffix}'


def build_allowed_origins(configured, site_url, domains):
    if configured is not None:
        values = configured
        if isinstance(values, str):
            try:
                values = json.loads(values) if values.lstrip().startswith('[') else values.split(',')
            except ValueError as exc:
                raise ImproperlyConfigured('WS_ALLOWED_ORIGINS contains invalid JSON') from exc
        if not isinstance(values, (list, tuple)):
            raise ImproperlyConfigured('WS_ALLOWED_ORIGINS must be a list of HTTP/HTTPS origins')
        try:
            return sorted({normalize_origin(value.strip()) for value in values})
        except (AttributeError, TypeError, ValueError) as exc:
            raise ImproperlyConfigured(
                'WS_ALLOWED_ORIGINS requires explicit HTTP/HTTPS origins without wildcards or paths'
            ) from exc

    # Use operator-configured domains, not ALLOWED_HOSTS or implicit debug hosts.
    values = [site_url] if site_url else []
    site = urlsplit(site_url) if site_url else None
    site_scheme = site.scheme if site else ''
    if site_scheme not in ('http', 'https'):
        site_scheme = 'https'
    loopback_hosts = {'localhost', '127.0.0.1', '::1'}
    site_is_loopback = site and (site.hostname or '').lower() in loopback_hosts
    for domain in (domains or '').split(','):
        domain = domain.strip()
        if not domain or '*' in domain or domain.startswith('.'):
            continue
        if '://' in domain:
            values.append(domain)
            continue
        netloc = domain
        if domain.count(':') > 1 and not domain.startswith('['):
            netloc = f'[{domain}]'
        host = (urlsplit(f'https://{netloc}').hostname or '').lower()
        # The default loopback SITE_URL is for local access; public domains use HTTPS.
        domain_scheme = 'https' if site_is_loopback and host not in loopback_hosts else site_scheme
        values.append(f'{domain_scheme}://{netloc}')
        if host in loopback_hosts and domain_scheme == 'https':
            values.append(f'http://{netloc}')
    try:
        return sorted({normalize_origin(value, allow_path=True) for value in values})
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            'Configure WS_ALLOWED_ORIGINS explicitly for the browser-facing site URLs'
        ) from exc
