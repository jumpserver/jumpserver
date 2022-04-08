from django.utils import timezone
from django.conf import settings
from django.core.exceptions import PermissionDenied

from authentication.models import TempToken
from .base import JMSModelBackend


class TempTokenAuthBackend(JMSModelBackend):
    model = TempToken

    def authenticate(self, request, username='', password='', *args, **kwargs):
        token = self.model.objects.filter(username=username, secret=password).first()
        if not token:
            return None
        if token.verified:
            raise PermissionDenied('Token has verified at: {}'.format(token.date_verified))

        token.verified = True
        token.date_verified = timezone.now()
        token.save()
        return token.user

    @staticmethod
    def is_enabled():
        return settings.AUTH_TEMP_TOKEN
