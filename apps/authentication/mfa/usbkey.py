import base64
import binascii
import json
import secrets
from urllib.parse import unquote

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from common.sdk.gm.soft_ukey import verify_usbkey_sm2_data
from .base import BaseMFA
from ..const import MFAType

usbkey_failed_msg = _('USBKey verification failed')
usbkey_challenge_expired_msg = _('USBKey challenge expired')
usbkey_unset_msg = _('USBKey unset')


class MFAUSBKey(BaseMFA):
    name = MFAType.USBKey.value
    display_name = MFAType.USBKey.name
    placeholder = _('USBKey signature payload')
    skip_cache_check = True

    def _cache_key(self):
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        return f'usbkey_mfa_challenge:{session_key}:{self.user.username}'

    @staticmethod
    def challenge_required():
        return True

    def send_challenge(self):
        if not self.is_authenticated():
            return {}
        challenge = base64.b16encode(secrets.token_bytes(32)).decode('ascii')
        cache.set(self._cache_key(), challenge, settings.VERIFY_CODE_TTL)
        return {'challenge': challenge}

    def _check_code(self, code):
        if not self.is_authenticated():
            return False, usbkey_failed_msg
        payload = self._decode_payload(code)
        if not payload:
            return False, usbkey_failed_msg

        challenge = cache.get(self._cache_key())
        if not challenge:
            return False, usbkey_challenge_expired_msg

        serial = payload.get('serial')
        user_key = self.user.user_usb_key.filter(u_key_serial=serial).first()
        if not user_key:
            return False, usbkey_unset_msg

        ok = verify_usbkey_sm2_data(user_key.u_key_public_key, challenge.encode('utf-8'), payload.get('signature'))
        if ok:
            cache.delete(self._cache_key())
            return True, ''
        return False, usbkey_failed_msg

    @staticmethod
    def _decode_payload(code):
        if not code:
            return None
        try:
            data = json.loads(code)
        except (TypeError, ValueError):
            try:
                data = json.loads(unquote(code))
            except (TypeError, ValueError):
                try:
                    padding = '=' * (-len(code) % 4)
                    raw = base64.urlsafe_b64decode((code + padding).encode('ascii'))
                    data = json.loads(raw.decode('utf-8'))
                except (binascii.Error, TypeError, ValueError, UnicodeDecodeError):
                    return None
        if not isinstance(data, dict):
            return None
        if not data.get('serial') or not data.get('signature'):
            return None
        return data

    def is_active(self):
        if not self.is_authenticated():
            return True
        return self.user.user_usb_key.exists()

    @staticmethod
    def global_enabled():
        return settings.SECURITY_MFA_BY_USBKEY

    def get_enable_url(self) -> str:
        return '/ui/#/profile/index'

    def get_disable_url(self) -> str:
        return '/ui/#/profile/index'

    def disable(self):
        pass

    def can_disable(self) -> bool:
        return False

    @staticmethod
    def help_text_of_enable():
        return _('Bind USBKey to enable')

    @staticmethod
    def help_text_of_disable():
        return _('Unbind USBKey to disable')
