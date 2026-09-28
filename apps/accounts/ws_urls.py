from django.urls import path

from accounts.ws import CredentialClientAuthMiddleware, CredentialEventConsumer


urlpatterns = [
    path(
        'ws/accounts/credential-events/',
        CredentialClientAuthMiddleware(CredentialEventConsumer.as_asgi()),
        name='credential-event-stream',
    ),
]
