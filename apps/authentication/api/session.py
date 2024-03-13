import time
from threading import Thread

from django.conf import settings
from django.contrib.auth import logout
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response

from common.permissions import IsValidUser
from common.sessions.cache import user_session_manager
from common.utils import get_logger

__all__ = ['UserSessionApi']

logger = get_logger(__name__)


class UserSessionManager:

    def __init__(self, request):
        self.request = request
        self.session = request.session

    def connect(self):
        user_session_manager.add_or_increment(self.session.session_key)

    def disconnect(self):
        user_session_manager.decrement_or_remove(self.session.session_key)
        if self.should_delete_session():
            thread = Thread(target=self.delay_delete_session)
            thread.start()

    def should_delete_session(self):
        return (self.session.modified or settings.SESSION_SAVE_EVERY_REQUEST) and \
            not self.session.is_empty() and \
            self.session.get_expire_at_browser_close() and \
            not user_session_manager.check_active(self.session.session_key)

    def delay_delete_session(self):
        timeout = 6
        check_interval = 0.5

        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(check_interval)
            if user_session_manager.check_active(self.session.session_key):
                return

        logout(self.request)


class UserSessionApi(generics.RetrieveDestroyAPIView):
    permission_classes = (IsValidUser,)

    def retrieve(self, request, *args, **kwargs):
        UserSessionManager(request).connect()
        return Response(status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        UserSessionManager(request).disconnect()
        return Response(status=status.HTTP_204_NO_CONTENT)
