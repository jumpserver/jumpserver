import os
from importlib import import_module

import django
import socket
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.conf import settings
from channels.routing import get_default_application
from django.core.handlers.asgi import ASGIRequest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from common.utils import get_logger

logger = get_logger(__name__)

class UnixSocketAuthMiddleware:
    def __init__(self, app):
        self.app = app
        header = os.environ.get('JMS_UNIX_SOCKET_AUTH_HEADER', 'x-jms-unix-token')
        self.header_name = header.lower().encode()
        self.header_value = os.environ.get('JMS_UNIX_SOCKET_AUTH_TOKEN', settings.BOOTSTRAP_TOKEN)

    async def __call__(self, scope, receive, send):
        if not self._is_unix_request(scope, receive):
            return await self.app(scope, receive, send)

        logger.debug("Received request on Unix socket, performing authentication...")
        request = ASGIRequest(scope, None)
        user = await self.authenticate(request)
        if user is None:
            return await self._reject(send)

        if user:
            scope['user'] = user
            scope = await self._set_authenticated_session(scope, user)

        return await self.app(scope, receive, send)

    async def authenticate(self, request):
        if self._match_static_token(request):
            return await self._get_admin_user()
        return None

    @staticmethod
    def _is_unix_request(scope, receive):
        try:
            transport = scope.get('extensions', {}).get('transport')
            if not transport and receive:
                protocol = getattr(receive, '__self__', None)
                if protocol:
                    transport = getattr(protocol, 'transport', None)

            if transport:
                sock = transport.get_extra_info('socket')
                if sock and getattr(sock, 'family', None) == socket.AF_UNIX:
                    return True
        except Exception:
            pass

        # Fallback for servers that expose unix socket path in ASGI scope.
        server = scope.get('server')
        if isinstance(server, (list, tuple)) and server:
            return isinstance(server[0], str) and server[0].endswith('.sock')
        return False

    def _match_static_token(self, request):
        if not self.header_value:
            return False
        header_value = request.headers.get(self.header_name.decode(), '')
        return header_value == self.header_value

    @sync_to_async
    def _get_admin_user(self):
        user_model = get_user_model()
        return user_model.objects.filter(username='admin').first()

    @sync_to_async
    def _set_authenticated_session(self, scope, user):
        session_store = import_module(settings.SESSION_ENGINE).SessionStore
        request = ASGIRequest(scope, None)
        request.session = session_store()
        request.user = user

        backend = getattr(settings, 'AUTH_BACKEND_MODEL', settings.AUTHENTICATION_BACKENDS[0])
        auth_login(request, user, backend=backend)
        request.session.save()

        session_cookie = f'{settings.SESSION_COOKIE_NAME}={request.session.session_key}'
        headers = []
        cookie_value = ''
        for key, value in scope.get('headers', []):
            if key.lower() == b'cookie':
                cookie_value = value.decode('latin1')
                continue
            headers.append((key, value))

        if cookie_value:
            cookie_value = f'{cookie_value}; {session_cookie}'
        else:
            cookie_value = session_cookie

        headers.append((b'cookie', cookie_value.encode('latin1')))
        scope['headers'] = headers
        return scope

    @staticmethod
    async def _reject(send):
        body = b'Unauthorized'
        await send({
            'type': 'http.response.start',
            'status': 401,
            'headers': [
                (b'content-type', b'text/plain; charset=utf-8'),
                (b'content-length', str(len(body)).encode()),
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })

application = UnixSocketAuthMiddleware(get_default_application())
