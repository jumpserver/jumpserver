from django.urls import path

from .. import ws

app_name = 'notifications'

urlpatterns = [
    path('ws/notifications/site-msg/', ws.SiteMsgWebsocket.as_asgi(), name='site-msg-ws'),
]
