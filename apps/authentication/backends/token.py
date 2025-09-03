from django.utils import timezone
from django.conf import settings
from django.core.exceptions import PermissionDenied

from authentication.models import TempToken
from .base import JMSBaseAuthBackend


class TempTokenAuthBackend(JMSBaseAuthBackend):
    model = TempToken

    @staticmethod
    def is_enabled():
        return settings.AUTH_TEMP_TOKEN

    def authenticate(self, request, username='', password=''):
        tokens = self.model.objects.filter(username=username).order_by('-date_created')[:500]
        token = next((t for t in tokens if t.secret == password), None)

        if not token:
            return None
        if not token.is_valid:
            raise PermissionDenied('Token is invalid, expired at {}'.format(token.date_expired))

        token.verified = True
        token.date_verified = timezone.now()
        token.save()
        return token.user

