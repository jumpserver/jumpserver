# ~*~ coding: utf-8 ~*~
import time

from django.urls import reverse_lazy, reverse
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth import logout as auth_logout
from django.conf import settings
from django.http.response import HttpResponseForbidden

from authentication.mixins import AuthMixin
from users.models import User
from common.utils import get_logger, get_object_or_none
from common.permissions import IsValidUser
from ... import forms
from .password import UserVerifyPasswordView
from ...utils import (
    generate_otp_uri, check_otp_code, get_user_or_pre_auth_user,
    is_auth_password_time_valid, is_auth_otp_time_valid
)

__all__ = [
    'UserOtpEnableStartView',
    'UserOtpEnableInstallAppView',
    'UserOtpEnableBindView', 'UserOtpSettingsSuccessView',
    'UserDisableMFAView', 'UserOtpUpdateView',
]

logger = get_logger(__name__)


class UserOtpEnableStartView(UserVerifyPasswordView):
    template_name = 'users/user_otp_check_password.html'

    def get_success_url(self):
        if settings.OTP_IN_RADIUS:
            success_url = reverse_lazy('authentication:user-otp-settings-success')
        else:
            success_url = reverse('authentication:user-otp-enable-install-app')
        return success_url


class UserOtpEnableInstallAppView(TemplateView):
    template_name = 'users/user_otp_enable_install_app.html'

    def get_context_data(self, **kwargs):
        user = get_user_or_pre_auth_user(self.request)
        context = {'user': user}
        kwargs.update(context)
        return super().get_context_data(**kwargs)





class UserOtpEnableBindView(AuthMixin, TemplateView, FormView):
    template_name = 'users/user_otp_enable_bind.html'
    form_class = forms.UserCheckOtpCodeForm
    success_url = reverse_lazy('authentication:user-otp-settings-success')

    def get(self, request, *args, **kwargs):
        if self._check_can_bind():
            return super().get(request, *args, **kwargs)
        return HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        if self._check_can_bind():
            return super().post(request, *args, **kwargs)
        return HttpResponseForbidden()

    def _check_authenticated_user_can_bind(self):
        user = self.request.user
        session = self.request.session

        if not user.mfa_enabled:
            return is_auth_password_time_valid(session)

        if not user.otp_secret_key:
            return is_auth_password_time_valid(session)

        return is_auth_otp_time_valid(session)

    def _check_unauthenticated_user_can_bind(self):
        session_user = None
        if not self.request.session.is_empty():
            user_id = self.request.session.get('user_id')
            session_user = get_object_or_none(User, pk=user_id)

        if session_user:
            if all((is_auth_password_time_valid(self.request.session), session_user.mfa_enabled, not session_user.otp_secret_key)):
                return True
        return False

    def _check_can_bind(self):
        if self.request.user.is_authenticated:
            return self._check_authenticated_user_can_bind()
        else:
            return self._check_unauthenticated_user_can_bind()

    def form_valid(self, form):
        otp_code = form.cleaned_data.get('otp_code')
        otp_secret_key = self.request.session.get('otp_secret_key', '')

        valid = check_otp_code(otp_secret_key, otp_code)
        if valid:
            self.save_otp(otp_secret_key)
            return super().form_valid(form)
        else:
            error = _("MFA code invalid, or ntp sync server time")
            form.add_error("otp_code", error)
            return self.form_invalid(form)

    def save_otp(self, otp_secret_key):
        user = get_user_or_pre_auth_user(self.request)
        user.enable_mfa()
        user.otp_secret_key = otp_secret_key
        user.save()

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


class UserDisableMFAView(FormView):
    template_name = 'users/user_verify_mfa.html'
    form_class = forms.UserCheckOtpCodeForm
    success_url = reverse_lazy('authentication:user-otp-settings-success')
    permission_classes = [IsValidUser]

    def form_valid(self, form):
        user = self.request.user
        otp_code = form.cleaned_data.get('otp_code')

        valid = user.check_mfa(otp_code)
        if valid:
            user.disable_mfa()
            user.save()
            return super().form_valid(form)
        else:
            error = _('MFA code invalid, or ntp sync server time')
            form.add_error('otp_code', error)
            return super().form_invalid(form)


class UserOtpUpdateView(FormView):
    template_name = 'users/user_verify_mfa.html'
    form_class = forms.UserCheckOtpCodeForm
    success_url = reverse_lazy('authentication:user-otp-enable-bind')
    permission_classes = [IsValidUser]

    def form_valid(self, form):
        user = self.request.user
        otp_code = form.cleaned_data.get('otp_code')

        valid = user.check_mfa(otp_code)
        if valid:
            self.request.session['auth_opt_expired_at'] = time.time() + settings.AUTH_EXPIRED_SECONDS
            return super().form_valid(form)
        else:
            error = _('MFA code invalid, or ntp sync server time')
            form.add_error('otp_code', error)
            return super().form_invalid(form)


class UserOtpSettingsSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        title, describe = self.get_title_describe()
        context = {
            'title': title,
            'messages': describe,
            'interval': 1,
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_title_describe(self):
        user = get_user_or_pre_auth_user(self.request)
        if self.request.user.is_authenticated:
            auth_logout(self.request)
        title = _('MFA enable success')
        describe = _('MFA enable success, return login page')
        if not user.mfa_enabled:
            title = _('MFA disable success')
            describe = _('MFA disable success, return login page')
        return title, describe

