from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from ops.urls.ws_urls import urlpatterns as ops_urlpatterns
from notifications.urls.ws_urls import urlpatterns as notifications_urlpatterns

urlpatterns = []
urlpatterns += ops_urlpatterns \
               + notifications_urlpatterns

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(urlpatterns)
    ),
})
