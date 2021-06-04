from django.urls import path

from .. import ws

app_name = 'notifications'

urlpatterns = [
    path('ws/notifications/site-msg/unread-count/',
         ws.UnreadSiteMsgCountWebsocket, name='unread-site-msg-count-ws'),
]
