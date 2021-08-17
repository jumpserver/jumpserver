from django.urls import path

from .. import ws

app_name = 'notifications'

urlpatterns = [
    path('ws/notifications/site-msg/', ws.SiteMsgWebsocket, name='site-msg-ws'),
]