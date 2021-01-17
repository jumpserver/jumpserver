from django.urls import path

from .. import ws

app_name = 'ops'

urlpatterns = [
    path('ws/ops/tasks/log/', ws.TaskLogWebsocket, name='task-log-ws'),
]
