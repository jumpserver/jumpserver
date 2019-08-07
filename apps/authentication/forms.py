# -*- coding: utf-8 -*-
#

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from captcha.fields import CaptchaField
from django.conf import settings
from users.utils import get_login_failed_count


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(label=_('Username'), max_length=100)
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=128, strip=False
    )

    error_messages = {
        'invalid_login': _(
            "The username or password you entered is incorrect, "
            "please enter it again."
        ),
        'inactive': _("This account is inactive."),
        'limit_login': _(
            "You can also try {times_try} times "
            "(The account will be temporarily locked for {block_time} minutes)"
        ),
        'block_login': _(
            "The account has been locked "
            "(please contact admin to unlock it or try again after {} minutes)"
        )
    }

    def confirm_login_allowed(self, user):
        if not user.is_staff:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',)

    def get_limit_login_error_message(self, username, ip):
        times_up = settings.SECURITY_LOGIN_LIMIT_COUNT
        times_failed = get_login_failed_count(username, ip)
        times_try = int(times_up) - int(times_failed)
        block_time = settings.SECURITY_LOGIN_LIMIT_TIME
        if times_try <= 0:
            error_message = self.error_messages['block_login']
            error_message = error_message.format(block_time)
        else:
            error_message = self.error_messages['limit_login']
            error_message = error_message.format(
                times_try=times_try, block_time=block_time,
            )
        return error_message

    def add_limit_login_error(self, username, ip):
        error = self.get_limit_login_error_message(username, ip)
        self.add_error('password', error)


class UserLoginCaptchaForm(UserLoginForm):
    captcha = CaptchaField()


class UserCheckOtpCodeForm(forms.Form):
    otp_code = forms.CharField(label=_('MFA code'), max_length=6)
