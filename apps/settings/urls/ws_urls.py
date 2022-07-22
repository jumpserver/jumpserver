from django.urls import path

from .. import ws

app_name = 'common'

urlpatterns = [
    path('ws/setting/ping/', ws.PingMsgWebsocket.as_asgi(), name='setting-ping-ws'),
    path('ws/setting/telnet/', ws.TelnetMsgWebsocket.as_asgi(), name='setting-telnet-ws'),
]
