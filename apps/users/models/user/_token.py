import base64

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from common.utils import (
    get_logger,
    random_string,
)

logger = get_logger(__file__)


class TokenMixin:
    CACHE_KEY_USER_RESET_PASSWORD_PREFIX = "_KEY_USER_RESET_PASSWORD_{}"
    email = ""
    id = None

    @property
    def private_token(self):
        return self.create_private_token()

    def create_private_token(self):
        from authentication.models import PrivateToken

        token, created = PrivateToken.objects.get_or_create(user=self)
        return token

    def delete_private_token(self):
        from authentication.models import PrivateToken

        PrivateToken.objects.filter(user=self).delete()

    def refresh_private_token(self):
        self.delete_private_token()
        return self.create_private_token()

    def create_bearer_token(self, request=None):
        expiration = settings.TOKEN_EXPIRATION or 3600
        if request:
            remote_addr = request.META.get("REMOTE_ADDR", "")
        else:
            remote_addr = "0.0.0.0"
        if not isinstance(remote_addr, bytes):
            remote_addr = remote_addr.encode("utf-8")
        remote_addr = base64.b16encode(remote_addr)  # .replace(b'=', '')
        cache_key = "%s_%s" % (self.id, remote_addr)
        token = cache.get(cache_key)
        if not token:
            token = random_string(36)
        cache.set(token, self.id, expiration)
        cache.set("%s_%s" % (self.id, remote_addr), token, expiration)
        date_expired = timezone.now() + timezone.timedelta(seconds=expiration)
        return token, date_expired

    def refresh_bearer_token(self, token):
        pass

    def create_access_key(self):
        access_key = self.access_keys.create()
        return access_key

    @property
    def access_key(self):
        return self.access_keys.first()

    def generate_reset_token(self):
        token = random_string(50)
        key = self.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        cache.set(key, {"id": self.id, "email": self.email}, 3600)
        return token

    @classmethod
    def validate_reset_password_token(cls, token):
        if not token:
            return None
        key = cls.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        value = cache.get(key)
        if not value:
            return None
        try:
            user_id = value.get("id", "")
            email = value.get("email", "")
            user = cls.objects.get(id=user_id, email=email)
            return user
        except (AttributeError, cls.DoesNotExist) as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def expired_reset_password_token(cls, token):
        key = cls.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        cache.delete(key)

