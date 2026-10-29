"""Bounded public-client registration for the configured Agent MCP resource."""
import time
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import DatabaseError, transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.compat import login_not_required
from oauth2_provider.models import get_application_model
from oauth2_provider.views.dynamic_client_registration import _build_application_kwargs, _parse_metadata
from redis.exceptions import RedisError

from common.utils.lock import DistributedLock
from common.validators import validate_mcp_resource_url
from terminal.models import AgentApplication

SCOPE = 'agent:access'
MAX_BODY_BYTES = 8192
MAX_REDIRECTS = 4
MAX_CLIENTS = 4096
REGISTRATIONS_PER_MINUTE = 30
REGISTRATION_LOCK = 'agent-oauth-client-registration'


def configured_resource():
    if not settings.MCP_ENABLED or not settings.MCP_DCR_ENABLED:
        return ''
    value = settings.MCP_PUBLIC_URL
    try:
        return validate_mcp_resource_url(value)
    except ValidationError as exc:
        raise ImproperlyConfigured('MCP_DCR_ENABLED requires the exact public MCP_PUBLIC_URL without query or fragment') from exc


def _error(error, description, status=400, retry_after=None):
    response = JsonResponse({'error': error, 'error_description': description}, status=status)
    if retry_after is not None:
        response['Retry-After'] = str(retry_after)
    return response


def _valid_callback(value):
    if not isinstance(value, str) or not value or len(value) > 2048:
        return False
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value) or any(c in value for c in '\\#*'):
        return False
    try:
        uri = urlsplit(value)
        return bool(
            value.startswith('http://') and uri.hostname in ('127.0.0.1', '::1')
            and uri.username is None and uri.password is None and uri.path.startswith('/')
            and not uri.netloc.endswith(':') and (uri.port is None or 1 <= uri.port <= 65535)
        )
    except ValueError:
        return False


def _metadata(body):
    try:
        data, error = _parse_metadata(body)
    except (UnicodeDecodeError, RecursionError):
        return None, _error('invalid_client_metadata', 'Request body must be valid UTF-8 JSON')
    if error:
        return None, error
    kwargs, error = _build_application_kwargs(data)
    if error:
        return None, error
    if kwargs['client_type'] != 'public' or kwargs['authorization_grant_type'] != 'authorization-code':
        return None, _error('invalid_client_metadata', 'Only public authorization-code clients are supported')
    if data.get('response_types', ['code']) != ['code'] or data.get('scope', SCOPE) != SCOPE:
        return None, _error('invalid_client_metadata', 'Only code responses and agent:access scope are supported')
    redirects = data['redirect_uris']
    if not 1 <= len(redirects) <= MAX_REDIRECTS or not all(_valid_callback(uri) for uri in redirects):
        return None, _error('invalid_redirect_uri', 'Provide at most four exact HTTP IP-loopback callback URIs')
    name = kwargs['name']
    if (not isinstance(name, str) or len(name) > 128 or any(ord(c) < 32 or ord(c) == 127 for c in name)
            or name == settings.OAUTH2_PROVIDER_JUMPSERVER_CLIENT_NAME):
        return None, _error('invalid_client_metadata', 'Invalid or reserved client name')
    kwargs['name'] = name or 'MCP client'
    return kwargs, None


class RegistrationUnavailable(Exception):
    pass


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_not_required, name='dispatch')
class AgentClientRegistrationView(View):
    http_method_names = ['post', 'options']

    def dispatch(self, request, *args, **kwargs):
        if not configured_resource():
            response = _error('not_found', 'Automatic Agent client registration is disabled', 404)
        else:
            response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response

    def post(self, request):
        # A shared fixed window bounds anonymous work without allocating one
        # cache entry for each attacker-supplied client or forwarded address.
        try:
            key = f'agent-dcr-rate:{int(time.time()) // 60}'
            count = 1 if cache.add(key, 1, timeout=120) else cache.incr(key)
        except (RedisError, ValueError):
            return _error('temporarily_unavailable', 'Registration capacity is unavailable', 503)
        if count > REGISTRATIONS_PER_MINUTE:
            return _error('temporarily_unavailable', 'Registration rate exceeded', 429, 60)
        if request.content_type != 'application/json':
            return _error('invalid_client_metadata', 'Content-Type must be application/json', 415)
        body = request.read(MAX_BODY_BYTES + 1)
        if len(body) > MAX_BODY_BYTES:
            return _error('invalid_client_metadata', 'Registration metadata exceeds 8 KiB', 413)
        kwargs, error = _metadata(body)
        if error:
            return error
        resource = configured_resource()
        if not resource:
            return _error('not_found', 'Automatic Agent client registration is disabled', 404)
        Application = get_application_model()
        lock = DistributedLock(REGISTRATION_LOCK, expire=30)
        acquired = False
        try:
            acquired = lock.acquire(blocking=False)
            if not acquired:
                return _error('temporarily_unavailable', 'Registration is busy', 429, 1)
            with transaction.atomic():
                if AgentApplication.objects.filter(application__registration_source=Application.RegistrationSource.DCR).count() >= MAX_CLIENTS:
                    return _error('temporarily_unavailable', 'Registered client capacity reached', 429, 60)
                application = Application(
                    registration_source=Application.RegistrationSource.DCR,
                    client_secret='', hash_client_secret=False, skip_authorization=False, **kwargs,
                )
                # The profile above admits only literal loopback callbacks.
                # Validate this instance without changing other OAuth clients'
                # process-wide redirect policy or skipping model validation.
                application.get_allowed_schemes = lambda: ['http']
                try:
                    application.full_clean()
                finally:
                    del application.get_allowed_schemes
                application.save()
                AgentApplication.objects.create(application=application, resource=resource)
                if not lock.locked_by_me():
                    raise RegistrationUnavailable
        except ValidationError:
            return _error('invalid_client_metadata', 'Invalid client metadata')
        except (RedisError, DatabaseError, RegistrationUnavailable):
            return _error('temporarily_unavailable', 'Client registration is unavailable', 503)
        finally:
            if acquired:
                try:
                    lock.release()
                except RedisError:
                    # The bounded lease expires; the database transaction has
                    # already committed or rolled back independently.
                    pass
        return JsonResponse({
            'client_id': application.client_id,
            'client_id_issued_at': int(application.created.timestamp()),
            'client_name': application.name,
            'redirect_uris': application.redirect_uris.split(),
            'grant_types': ['authorization_code', 'refresh_token'],
            'response_types': ['code'],
            'token_endpoint_auth_method': 'none',
            'scope': SCOPE,
        }, status=201)
