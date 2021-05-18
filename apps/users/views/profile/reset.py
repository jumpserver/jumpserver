# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals
from django.views.generic import RedirectView
from django.shortcuts import reverse, redirect
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import FormView

from common.utils import get_object_or_none, FlashMessageUtil
from common.permissions import IsValidUser
from common.mixins.views import PermissionsMixin
from ...models import User
from ...utils import (
    send_reset_password_mail, get_password_check_rules, check_password_rules,
    send_reset_password_success_mail
)
from ... import forms


__all__ = [
    'UserLoginView', 'UserResetPasswordView', 'UserForgotPasswordView', 'UserFirstLoginView',
]


class UserLoginView(RedirectView):
    url = reverse_lazy('authentication:login')
    query_string = True


class UserForgotPasswordView(FormView):
    template_name = 'users/forgot_password.html'
    form_class = forms.UserForgotPasswordForm

    @staticmethod
    def get_redirect_message_url():
        message_data = {
            'title': _('Send reset password message'),
            'message': _('Send reset password mail success, '
                         'login your mail box and follow it '),
            'redirect_url': reverse('authentication:login'),
        }
        url = FlashMessageUtil.gen_message_url(message_data)
        return url

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = get_object_or_none(User, email=email)
        if not user:
            error = _('Email address invalid, please input again')
            form.add_error('email', error)
            return self.form_invalid(form)

        if not user.is_local:
            error = _(
                'The user is from {}, please go to the corresponding system to change the password'
            ).format(user.get_source_display())
            form.add_error('email', error)
            return self.form_invalid(form)
        send_reset_password_mail(user)
        url = self.get_redirect_message_url()
        return redirect(url)


class UserResetPasswordView(FormView):
    template_name = 'users/reset_password.html'
    form_class = forms.UserTokenResetPasswordForm

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        errors = kwargs.get('errors')
        if errors:
            context['errors'] = errors
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.request.GET.get('token', '')
        user = User.validate_reset_password_token(token)
        if not user:
            context['errors'] = _('Token invalid or expired')
            context['token_invalid'] = True
        check_rules = get_password_check_rules()
        context['password_check_rules'] = check_rules
        return context

    def form_valid(self, form):
        token = self.request.GET.get('token')
        user = User.validate_reset_password_token(token)
        if not user:
            error = _('Token invalid or expired')
            form.add_error('new_password', error)
            return self.form_invalid(form)

        if not user.can_update_password():
            error = _('User auth from {}, go there change password')
            form.add_error('new_password', error.format(user.get_source_display()))
            return self.form_invalid(form)

        password = form.cleaned_data['new_password']
        is_ok = check_password_rules(password)
        if not is_ok:
            error = _('* Your password does not meet the requirements')
            form.add_error('new_password', error)
            return self.form_invalid(form)

        if user.is_history_password(password):
            limit_count = settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT
            error = _('* The new password cannot be the last {} passwords').format(limit_count)
            form.add_error('new_password', error)
            return self.form_invalid(form)

        user.reset_password(password)
        User.expired_reset_password_token(token)
        send_reset_password_success_mail(self.request, user)
        url = self.get_redirect_url()
        return redirect(url)

    @staticmethod
    def get_redirect_url():
        message_data = {
            'title': _('Reset password success'),
            'message': _('Reset password success, return to login page'),
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        return FlashMessageUtil.gen_message_url(message_data)


class UserFirstLoginView(PermissionsMixin, TemplateView):
    template_name = 'users/first_login.html'
    permission_classes = [IsValidUser]
