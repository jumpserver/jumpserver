from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import WebsocketDenier
from django.core.asgi import get_asgi_application
from django.core.handlers.asgi import ASGIRequest
from django.conf import settings
from django.contrib.auth import get_user, get_user_model
from django.utils.module_loading import import_string
from django.utils import timezone
from types import SimpleNamespace

from authentication.backends.drf import (
    SignatureAuthentication,
    AccessTokenAuthentication,
    OAuth2Authentication,
)
from notifications.urls.ws_urls import urlpatterns as notifications_urlpatterns
from ops.urls.ws_urls import urlpatterns as ops_urlpatterns
from settings.urls.ws_urls import urlpatterns as setting_urlpatterns
from terminal.urls.ws_urls import urlpatterns as terminal_urlpatterns
from accounts.ws_urls import urlpatterns as accounts_urlpatterns
from common.utils import get_logger
from .ws_origin import build_allowed_origins, normalize_origin
import socket

logger = get_logger(__name__)

__all__ = ['urlpatterns', 'application']

urlpatterns = accounts_urlpatterns + \
              ops_urlpatterns + \
              notifications_urlpatterns + \
              setting_urlpatterns + \
              terminal_urlpatterns

if settings.XPACK_ENABLED:
    urlpatterns += import_string('xpack.urls.ws_urls.urlpatterns')


@database_sync_to_async
def get_signature_user(scope):
    headers = dict(scope["headers"])
    if not headers.get(b'authorization'):
        return
    if scope['type'] == 'websocket':
        scope['method'] = 'GET'
    # 因为 ws 使用的是 scope，所以需要转换成 request 对象，用于认证校验
    request = ASGIRequest(scope, None)
    backends = [SignatureAuthentication(),
                AccessTokenAuthentication(),
                OAuth2Authentication()]
    for backend in backends:
        try:
            result = backend.authenticate(request)
            if not result:
                continue
            user, _ = result
            if user:
                session = getattr(request, 'client_login_session', None)
                if session is not None:
                    scope['client_login_session_id'] = session.pk
                return user
        except Exception:
            logger.debug('WebSocket authentication failed for %s', backend.__class__.__name__)
    return None


class WsSignatureAuthMiddleware:
    def __init__(self, app):
        self.app = app
        self.allowed_origins = None
        if settings.WS_ALLOWED_ORIGINS is not None:
            self.allowed_origins = build_allowed_origins(settings.WS_ALLOWED_ORIGINS, '', '')

    async def __call__(self, scope, receive, send):
        origins = [value for name, value in scope.get('headers', []) if name == b'origin']
        if origins:
            allowed_origins = self.allowed_origins
            if allowed_origins is None:
                # SITE_URL can be updated from database settings after startup.
                allowed_origins = build_allowed_origins(None, settings.SITE_URL, settings.CONFIG.DOMAINS)
            try:
                valid_origin = (
                    len(origins) == 1
                    and (
                        '*' in allowed_origins
                        or normalize_origin(origins[0].decode('ascii')) in allowed_origins
                    )
                )
            except (UnicodeDecodeError, ValueError):
                valid_origin = False
            if not valid_origin:
                return await WebsocketDenier()(scope, receive, send)

        user = await get_signature_user(scope)
        if user and (not user.is_authenticated or not user.is_valid):
            user = None
        # Native clients may omit Origin, but a browser session cookie is not
        # sufficient: only successful header authentication can use this path.
        if not origins and not user:
            return await WebsocketDenier()(scope, receive, send)
        if user:
            scope['user'] = user
            scope['header_authenticated'] = True
        return await self.app(scope, receive, send)


@database_sync_to_async
def websocket_session_allowed(scope):
    user = scope.get('user')
    if user is None or not user.is_authenticated:
        return True  # The routed consumer retains its own authentication policy.
    if scope.get('header_authenticated'):
        # A long-lived connection must not retain an account that has been disabled.
        current_user = get_user_model().objects.filter(pk=user.pk).first()
        if current_user is None or not current_user.is_valid:
            return False
        scope['user'] = current_user
        session_id = scope.get('client_login_session_id')
        if session_id is None:
            return True
        from authentication.services.client_login_session import validate_session
        return validate_session(session_id, allow_locked=False)
    session = scope.get('session')
    if session is None or not session.session_key:
        return False
    # Reload instead of trusting the identity cached when the socket connected.
    data = session.load()
    session._session_cache = data
    if data.get('_auth_user_id') != str(user.pk):
        return False
    # Reuse HTTP authentication: reload the user and verify the current password hash.
    current_user = get_user(SimpleNamespace(session=session))
    if not current_user.is_authenticated or not current_user.is_valid or current_user.pk != user.pk:
        return False
    scope['user'] = current_user
    if any(data.get(name) for name in ('auth_mfa_required', 'auth_third_party_required', 'auth_confirm_required')):
        return False
    from common.sessions import session_expiry
    expires_at = session_expiry(session.session_key)
    if expires_at is not None and timezone.now() >= expires_at:
        return False
    return True


@database_sync_to_async
def websocket_screen_locked(scope):
    if scope.get('header_authenticated'):
        return False
    user = scope.get('user')
    session = scope.get('session')
    if user is None or not user.is_authenticated or session is None or not session.session_key:
        return False
    from common.sessions import policy_locked
    return policy_locked(session.login_policy)


class WsSessionSecurityMiddleware:
    """Keep locked Web sockets connected, but reject input until unlocked."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        closed = False

        async def check_session():
            nonlocal closed
            if closed:
                return False
            allowed = await websocket_session_allowed(scope)
            if closed:
                return False
            if allowed:
                return True
            closed = True
            await send({'type': 'websocket.close', 'code': 1008})
            return False

        async def receive_checked():
            while True:
                event = await receive()
                if event['type'] != 'websocket.receive':
                    return event
                if not await check_session():
                    return {'type': 'websocket.disconnect', 'code': 1008}
                if not await websocket_screen_locked(scope):
                    return event
                # Do not replay commands entered while locked after unlocking.

        async def send_checked(event):
            if closed:
                return
            if event['type'] in ('websocket.accept', 'websocket.send') and not await check_session():
                return
            await send(event)

        if await check_session():
            return await self.app(scope, receive_checked, send_checked)


class SocketContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        fno = self._extract_socket_fno(scope, receive)

        if fno:
            logger.debug(f"Successfully extracted FNO: {fno}")
            scope['fno'] = fno

        return await self.app(scope, receive, send)

    @staticmethod
    def _extract_socket_fno(scope, receive) -> int:
        try:
            transport = scope.get('extensions', {}).get('transport')
            if not transport and receive:
                protocol = getattr(receive, "__self__", None)
                if protocol:
                    transport = getattr(protocol, "transport", None)

            if transport:
                sock = transport.get_extra_info('socket')
                if sock:
                    return sock.fileno()

        except Exception as e:
            logger.error(f"Internal error during FNO extraction: {e}")

        return None


application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": SocketContextMiddleware(
        get_asgi_application()
    ),

    # WebSocket chat handler
    "websocket": SocketContextMiddleware(
        WsSignatureAuthMiddleware(
            AuthMiddlewareStack(
                WsSessionSecurityMiddleware(URLRouter(urlpatterns))
            )
        )
    ),
})
