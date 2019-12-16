# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals


from django.contrib.auth import authenticate
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.edit import (
    UpdateView, FormView
)
from django.contrib.auth import logout as auth_logout

from common.utils import get_logger, ssh_key_gen
from common.permissions import (
    PermissionsMixin, IsValidUser,
    UserCanUpdatePassword, UserCanUpdateSSHKey,
)
from .. import forms
from ..models import User
from ..utils import generate_otp_uri, check_otp_code, \
    get_user_or_tmp_user, get_password_check_rules, check_password_rules

__all__ = [
    'UserProfileView',
    'UserProfileUpdateView', 'UserPasswordUpdateView',
    'UserPublicKeyUpdateView', 'UserPublicKeyGenerateView',
    'UserCheckPasswordView', 'UserOtpEnableInstallAppView',
    'UserOtpEnableBindView', 'UserOtpSettingsSuccessView',
    'UserDisableMFAView', 'UserOtpUpdateView',
]

logger = get_logger(__name__)


class UserProfileView(PermissionsMixin, TemplateView):
    template_name = 'users/user_profile.html'
    permission_classes = [IsValidUser]

    def get_context_data(self, **kwargs):
        mfa_setting = settings.SECURITY_MFA_AUTH
        context = {
            'action': _('Profile'),
            'mfa_setting': mfa_setting if mfa_setting is not None else False,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserProfileUpdateView(PermissionsMixin, UpdateView):
    template_name = 'users/user_profile_update.html'
    model = User
    permission_classes = [IsValidUser]
    form_class = forms.UserProfileForm
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': _('User'),
            'action': _('Profile setting'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserPasswordUpdateView(PermissionsMixin, UpdateView):
    template_name = 'users/user_password_update.html'
    model = User
    form_class = forms.UserPasswordForm
    success_url = reverse_lazy('users:user-profile')
    permission_classes = [IsValidUser, UserCanUpdatePassword]

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        check_rules = get_password_check_rules()
        context = {
            'app': _('Users'),
            'action': _('Password update'),
            'password_check_rules': check_rules,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        auth_logout(self.request)
        return super().get_success_url()

    def form_valid(self, form):
        password = form.cleaned_data.get('new_password')
        is_ok = check_password_rules(password)
        if not is_ok:
            form.add_error(
                "new_password",
                _("* Your password does not meet the requirements")
            )
            return self.form_invalid(form)
        return super().form_valid(form)


class UserPublicKeyUpdateView(PermissionsMixin, UpdateView):
    template_name = 'users/user_pubkey_update.html'
    model = User
    form_class = forms.UserPublicKeyForm
    permission_classes = [IsValidUser, UserCanUpdateSSHKey]
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Public key update'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserPublicKeyGenerateView(PermissionsMixin, View):
    permission_classes = [IsValidUser]

    def get(self, request, *args, **kwargs):
        private, public = ssh_key_gen(username=request.user.username, hostname='jumpserver')
        request.user.public_key = public
        request.user.save()
        response = HttpResponse(private, content_type='text/plain')
        filename = "{0}-jumpserver.pem".format(request.user.username)
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response


class UserCheckPasswordView(FormView):
    template_name = 'users/user_password_check.html'
    form_class = forms.UserCheckPasswordForm

    def form_valid(self, form):
        user = get_user_or_tmp_user(self.request)
        password = form.cleaned_data.get('password')
        user = authenticate(username=user.username, password=password)
        if not user:
            form.add_error("password", _("Password invalid"))
            return self.form_invalid(form)
        if not user.mfa_is_otp():
            user.enable_mfa()
            user.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        if settings.OTP_IN_RADIUS:
            success_url = reverse_lazy('users:user-otp-settings-success')
        else:
            success_url = reverse('users:user-otp-enable-install-app')
        return success_url


class UserOtpEnableInstallAppView(TemplateView):
    template_name = 'users/user_otp_enable_install_app.html'

    def get_context_data(self, **kwargs):
        user = get_user_or_tmp_user(self.request)
        context = {
            'user': user
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserOtpEnableBindView(TemplateView, FormView):
    template_name = 'users/user_otp_enable_bind.html'
    form_class = forms.UserCheckOtpCodeForm
    success_url = reverse_lazy('users:user-otp-settings-success')

    def get_context_data(self, **kwargs):
        user = get_user_or_tmp_user(self.request)
        otp_uri, otp_secret_key = generate_otp_uri(self.request)
        context = {
            'otp_uri': otp_uri,
            'otp_secret_key': otp_secret_key,
            'user': user
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        otp_code = form.cleaned_data.get('otp_code')
        otp_secret_key = cache.get(self.request.session.session_key+'otp_key', '')

        if check_otp_code(otp_secret_key, otp_code):
            self.save_otp(otp_secret_key)
            return super().form_valid(form)

        else:
            form.add_error("otp_code", _("MFA code invalid, or ntp sync server time"))
            return self.form_invalid(form)

    def save_otp(self, otp_secret_key):
        user = get_user_or_tmp_user(self.request)
        user.enable_mfa()
        user.otp_secret_key = otp_secret_key
        user.save()


class UserDisableMFAView(FormView):
    template_name = 'users/user_disable_mfa.html'
    form_class = forms.UserCheckOtpCodeForm
    success_url = reverse_lazy('users:user-otp-settings-success')

    def form_valid(self, form):
        user = self.request.user
        otp_code = form.cleaned_data.get('otp_code')

        valid = user.check_mfa(otp_code)
        if valid:
            user.disable_mfa()
            user.save()
            return super().form_valid(form)
        else:
            form.add_error('otp_code', _('MFA code invalid, or ntp sync server time'))
            return super().form_invalid(form)


class UserOtpUpdateView(UserDisableMFAView):
    success_url = reverse_lazy('users:user-otp-enable-bind')


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
        user = get_user_or_tmp_user(self.request)
        if self.request.user.is_authenticated:
            auth_logout(self.request)
        title = _('MFA enable success')
        describe = _('MFA enable success, return login page')
        if not user.mfa_enabled:
            title = _('MFA disable success')
            describe = _('MFA disable success, return login page')

        return title, describe

