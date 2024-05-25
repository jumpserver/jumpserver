# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .base import BaseMFA

usbkey_failed_msg = _("USBKey Serial Number verify invalid,")


class MFAUSBKey(BaseMFA):
    name = 'usbkey'
    display_name = 'USBKey'
    placeholder = _("USBKey verification")

    def check_code(self, code):
        assert self.is_authenticated()
        ok = False
        if self.user.usbkey_sn:
            if self.user.usbkey_sn == code:
                ok = True
        msg = '' if ok else usbkey_failed_msg
        return ok, msg

    def is_active(self):
        if not self.is_authenticated():
            return True
        return self.user.usbkey_sn

    @staticmethod
    def global_enabled():
        return settings.SECURITY_OTP_IN_USBKEY

    def get_enable_url(self) -> str:
        return ''

    def can_disable(self):
        return False

    def disable(self):
        return ''

    @staticmethod
    def help_text_of_disable():
        return _("USBKey global enabled, cannot disable")

    def get_disable_url(self) -> str:
        return ''
