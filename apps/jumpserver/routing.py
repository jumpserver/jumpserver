from notifications.urls.ws_urls import urlpatterns as notifications_urlpatterns
from ops.urls.ws_urls import urlpatterns as ops_urlpatterns
from settings.urls.ws_urls import urlpatterns as setting_urlpatterns
from terminal.urls.ws_urls import urlpatterns as terminal_urlpatterns

urlpatterns = ops_urlpatterns + \
              notifications_urlpatterns + \
              setting_urlpatterns + \
              terminal_urlpatterns
