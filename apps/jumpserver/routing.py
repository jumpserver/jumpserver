from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from ops.urls.ws_urls import urlpatterns as ops_urlpatterns

urlpatterns = [
]
urlpatterns += ops_urlpatterns

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter(urlpatterns)
    ),
})
