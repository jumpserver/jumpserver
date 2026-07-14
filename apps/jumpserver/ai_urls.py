from django.urls import include, path

from jumpserver.api import HealthCheckView


urlpatterns = [
    path('api/health/', HealthCheckView.as_view(), name='ai-health'),
    path('api/v1/chat-ai/', include('chat_ai.api.urls', namespace='ai-chat-ai')),
]

