from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.core.handlers.asgi import ASGIRequest

from authentication.backends.drf import (
    SignatureAuthentication,
    AccessTokenAuthentication
)
from notifications.urls.ws_urls import urlpatterns as notifications_urlpatterns
from ops.urls.ws_urls import urlpatterns as ops_urlpatterns
from settings.urls.ws_urls import urlpatterns as setting_urlpatterns
from terminal.urls.ws_urls import urlpatterns as terminal_urlpatterns

__all__ = ['urlpatterns', 'application']

urlpatterns = ops_urlpatterns + \
              notifications_urlpatterns + \
              setting_urlpatterns + \
              terminal_urlpatterns


@database_sync_to_async
def get_signature_user(scope):
    headers = dict(scope["headers"])
    if not headers.get(b'authorization'):
        return
    if scope['type'] == 'websocket':
        scope['method'] = 'GET'
    try:
        # 因为 ws 使用的是 scope，所以需要转换成 request 对象，用于认证校验
        request = ASGIRequest(scope, None)
        backends = [SignatureAuthentication(),
                    AccessTokenAuthentication()]
        for backend in backends:
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


application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": get_asgi_application(),

    # WebSocket chat handler
    "websocket": WsSignatureAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(urlpatterns)
        )
    ),
})
