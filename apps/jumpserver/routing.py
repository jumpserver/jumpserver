from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from ops.urls.ws_urls import urlpatterns as ops_urlpatterns
from notifications.urls.ws_urls import urlpatterns as notifications_urlpatterns
from settings.urls.ws_urls import urlpatterns as setting_urlpatterns
from terminal.urls.ws_urls import urlpatterns as terminal_urlpatterns

from .middleware import WsSignatureAuthMiddleware

urlpatterns = []
urlpatterns += ops_urlpatterns + \
               notifications_urlpatterns + \
               setting_urlpatterns + \
               terminal_urlpatterns

application = ProtocolTypeRouter({
    'websocket': WsSignatureAuthMiddleware(AuthMiddlewareStack(URLRouter(urlpatterns))),
    "http": get_asgi_application(),
})
