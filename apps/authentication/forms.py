# -*- coding: utf-8 -*-
#

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from captcha.fields import CaptchaField, CaptchaTextInput


class UserLoginForm(forms.Form):
    username = forms.CharField(label=_('Username'), max_length=100)
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=1024, strip=False
    )

    def confirm_login_allowed(self, user):
        if not user.is_staff:
            raise forms.ValidationError(
                self.error_messages['inactive'],
                code='inactive',
            )


class UserCheckOtpCodeForm(forms.Form):
    otp_code = forms.CharField(label=_('MFA code'), max_length=6)


class CustomCaptchaTextInput(CaptchaTextInput):
    template_name = 'authentication/_captcha_field.html'


class CaptchaMixin(forms.Form):
    captcha = CaptchaField(widget=CustomCaptchaTextInput)


class ChallengeMixin(forms.Form):
    challenge = forms.CharField(label=_('MFA code'), max_length=6,
                                required=False)


def get_user_login_form_cls(*, captcha=False):
    bases = []
    if settings.SECURITY_LOGIN_CAPTCHA_ENABLED and captcha:
        bases.append(CaptchaMixin)
    if settings.SECURITY_LOGIN_CHALLENGE_ENABLED:
        bases.append(ChallengeMixin)
    bases.append(UserLoginForm)
    return type('UserLoginForm', tuple(bases), {})
