# ~*~ coding: utf-8 ~*~
import time

from django.conf import settings
from django.contrib.auth import authenticate
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic.edit import UpdateView, FormView
from django.contrib.auth import logout as auth_logout

from common.utils import get_logger
from common.permissions import (
    PermissionsMixin, IsValidUser,
    UserCanUpdatePassword
)
from ... import forms
from ...models import User
from ...utils import (
    get_user_or_pre_auth_user,
    check_password_rules, get_password_check_rules,
)

__all__ = ['UserPasswordUpdateView', 'UserVerifyPasswordView']

logger = get_logger(__name__)


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


class UserVerifyPasswordView(FormView):
    template_name = 'users/user_password_verify.html'
    form_class = forms.UserCheckPasswordForm

    def form_valid(self, form):
        user = get_user_or_pre_auth_user(self.request)
        password = form.cleaned_data.get('password')
        user = authenticate(request=self.request, username=user.username, password=password)
        if not user:
            form.add_error("password", _("Password invalid"))
            return self.form_invalid(form)
        if not user.mfa_is_otp():
            user.enable_mfa()
            user.save()
        self.request.session['user_id'] = str(user.id)
        self.request.session['auth_password'] = 1
        self.request.session['auth_password_expired_at'] = time.time() + settings.AUTH_EXPIRED_SECONDS
        return redirect(self.get_success_url())

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        else:
            return referer

    def get_context_data(self, **kwargs):
        context = {
            'user': get_user_or_pre_auth_user(self.request)
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
