import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from .middleware import WsSignatureAuthMiddleware
from .routing import urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
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
