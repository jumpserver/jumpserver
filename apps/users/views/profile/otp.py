# ~*~ coding: utf-8 ~*~
import os

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils._os import safe_join
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from authentication.errors import SessionEmptyError
from authentication.mfa import MFAOtp, otp_failed_msg
from authentication.mixins import AuthMixin
from common.permissions import IsValidUser
from common.utils import get_logger, FlashMessageUtil
from common.views.mixins import PermissionsMixin
from ... import forms
from ...utils import (
    generate_otp_uri, check_otp_code,
    get_user_or_pre_auth_user,
)

__all__ = [
    'UserOtpEnableStartView',
    'UserOtpEnableInstallAppView',
    'UserOtpEnableBindView',
    'UserOtpDisableView',
]

logger = get_logger(__name__)


class UserOtpEnableStartView(AuthMixin, TemplateView):
    template_name = 'users/user_otp_check_password.html'

    def get(self, request, *args, **kwargs):
        try:
            self.get_user_from_session()
        except SessionEmptyError:
            url = reverse('authentication:login') + '?_=otp_enable_start'
            return redirect(url)
        return super().get(request, *args, **kwargs)


class UserOtpEnableInstallAppView(TemplateView):
    template_name = 'users/user_otp_enable_install_app.html'

    @staticmethod
    def replace_authenticator_png(platform):
        media_url = settings.MEDIA_URL
        base_path = f'img/authenticator_{platform}.png'
        authenticator_media_path = safe_join(settings.MEDIA_ROOT, base_path)
        if os.path.exists(authenticator_media_path):
            authenticator_url = f'{media_url}{base_path}'
        else:
            authenticator_url = static(base_path)
        return authenticator_url

    def get_context_data(self, **kwargs):
        user = get_user_or_pre_auth_user(self.request)
        authenticator_android_url = self.replace_authenticator_png('android')
        authenticator_iphone_url = self.replace_authenticator_png('iphone')
        context = {
            'user': user,
            'authenticator_android_url': authenticator_android_url,
            'authenticator_iphone_url': authenticator_iphone_url
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserOtpEnableBindView(AuthMixin, TemplateView, FormView):
    template_name = 'users/user_otp_enable_bind.html'
    form_class = forms.UserCheckOtpCodeForm

    def get(self, request, *args, **kwargs):
        pre_response = self._pre_check_can_bind()
        if pre_response:
            return pre_response
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        pre_response = self._pre_check_can_bind()
        if pre_response:
            return pre_response
        return super().post(request, *args, **kwargs)

    def _pre_check_can_bind(self):
        try:
            user = self.get_user_from_session()
        except Exception as e:
            verify_url = reverse('authentication:user-otp-enable-start') + f'?e={e}'
            return HttpResponseRedirect(verify_url)

        if user.otp_secret_key:
            return self.has_already_bound_message()
        return None

    @staticmethod
    def has_already_bound_message():
        message_data = {
            'title': _('Already bound'),
            'error': _('MFA already bound, disable first, then bound'),
            'interval': 10,
            'redirect_url': reverse('authentication:user-otp-disable'),
        }
        response = FlashMessageUtil.gen_and_redirect_to(message_data)
        return response

    def form_valid(self, form):
        otp_code = form.cleaned_data.get('otp_code')
        otp_secret_key = self.request.session.get('otp_secret_key', '')

        valid = check_otp_code(otp_secret_key, otp_code)
        if not valid:
            form.add_error("otp_code", otp_failed_msg)
            return self.form_invalid(form)

        self.save_otp(otp_secret_key)
        auth_logout(self.request)
        return super().form_valid(form)

    def save_otp(self, otp_secret_key):
        user = get_user_or_pre_auth_user(self.request)
        user.otp_secret_key = otp_secret_key
        user.save(update_fields=['otp_secret_key'])

    def get_success_url(self):
        message_data = {
            'title': _('OTP enable success'),
            'message': _('OTP enable success, return login page'),
            'interval': 5,
            'redirect_url': reverse('authentication:login'),
        }
        url = FlashMessageUtil.gen_message_url(message_data)
        return url

    def get_context_data(self, **kwargs):
        user = get_user_or_pre_auth_user(self.request)
        otp_uri, otp_secret_key = generate_otp_uri(user.username)
        self.request.session['otp_secret_key'] = otp_secret_key
        context = {
            'otp_uri': otp_uri,
            'otp_secret_key': otp_secret_key,
            'user': user
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserOtpDisableView(PermissionsMixin, FormView):
    template_name = 'users/user_verify_mfa.html'
    form_class = forms.UserCheckOtpCodeForm
    permission_classes = [IsValidUser]

    def form_valid(self, form):
        user = self.request.user
        otp_code = form.cleaned_data.get('otp_code')
        otp = MFAOtp(user)

        ok, error = otp.check_code(otp_code)
        if not ok:
            form.add_error('otp_code', error)
            return super().form_invalid(form)

        otp.disable()
        auth_logout(self.request)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': _("Disable OTP")
        })
        return context

    def get_success_url(self):
        message_data = {
            'title': _('OTP disable success'),
            'message': _('OTP disable success, return login page'),
            'interval': 5,
            'redirect_url': reverse('authentication:login'),
        }
        url = FlashMessageUtil.gen_message_url(message_data)
        return url
