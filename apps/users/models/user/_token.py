import base64

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from common.utils import (
    get_logger,
    random_string,
    text_hmac_sha256,
    get_request_ip
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

    def create_bearer_token(self, request=None, age=None):
        expiration = age or settings.TOKEN_EXPIRATION or 3600
        if request:
            remote_addr = get_request_ip(request)
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

    def generate_reset_token(self, *, for_password_reset=False):
        token = random_string(50)
        key = self.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        value = {"id": self.id, "email": self.email}
        timeout = 3600
        if for_password_reset:
            from authentication.password_reset import FLOW_TTL, key as recovery_key
            value['password_fingerprint'] = recovery_key('password', self.password)
            timeout = FLOW_TTL
        cache.set(key, value, timeout)
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
            email_lookup = text_hmac_sha256(email)
            user = cls.objects.get(id=user_id, email_lookup=email_lookup)
            if value.get('password_fingerprint'):
                from authentication.password_reset import key as recovery_key
                from django.utils.crypto import constant_time_compare
                if not constant_time_compare(
                    value['password_fingerprint'], recovery_key('password', user.password)
                ):
                    return None
            return user
        except (AttributeError, cls.DoesNotExist) as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def expired_reset_password_token(cls, token):
        key = cls.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        cache.delete(key)

