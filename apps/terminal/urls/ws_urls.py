from django.urls import path

from .. import ws

app_name = 'terminal'

urlpatterns = [
    path('ws/terminal-task/', ws.TerminalTaskWebsocket.as_asgi(), name='terminal-task-ws'),
]
