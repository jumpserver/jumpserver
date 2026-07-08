from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.core.handlers.asgi import ASGIRequest
from django.conf import settings

from authentication.backends.drf import (
    SignatureAuthentication,
    AccessTokenAuthentication
)
from notifications.urls.ws_urls import urlpatterns as notifications_urlpatterns
from ops.urls.ws_urls import urlpatterns as ops_urlpatterns
from settings.urls.ws_urls import urlpatterns as setting_urlpatterns
from terminal.urls.ws_urls import urlpatterns as terminal_urlpatterns
from common.utils import get_logger
import socket

logger = get_logger(__name__)

__all__ = ['urlpatterns', 'application']

urlpatterns = ops_urlpatterns + \
              notifications_urlpatterns + \
              setting_urlpatterns + \
              terminal_urlpatterns

if settings.XPACK_ENABLED:
    from xpack.plugins.cloud.urls.ws_urls import urlpatterns as xcloud_urlpatterns

    urlpatterns += xcloud_urlpatterns


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
                AccessTokenAuthentication()]
    for backend in backends:
        try:
            user, _ = backend.authenticate(request)
            if user:
                return user
        except Exception as e:
            print(e)
    return None


class WsSignatureAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        user = await get_signature_user(scope)
        if user:
            scope['user'] = user
        return await self.app(scope, receive, send)


class SocketContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        fno = self._extract_socket_fno(scope, receive)

        if fno:
            logger.debug(f"Successfully extracted FNO: {fno}")
            scope['fno'] = fno
        else:
            logger.debug(f"Failed to trace FNO for {scope.get('client')}")

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
                URLRouter(urlpatterns)
            )
        )
    ),
})
