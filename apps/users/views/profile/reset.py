# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals
from django.shortcuts import render
from django.views.generic import RedirectView
from django.core.files.storage import default_storage
from django.shortcuts import reverse, redirect
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView
from django.conf import settings
from django.urls import reverse_lazy
from formtools.wizard.views import SessionWizardView
from django.views.generic import FormView

from common.utils import get_object_or_none
from common.permissions import PermissionsMixin, IsValidUser
from ...models import User
from ...utils import (
    send_reset_password_mail, get_password_check_rules, check_password_rules
)
from ... import forms


__all__ = [
    'UserLoginView', 'UserForgotPasswordSendmailSuccessView',
    'UserResetPasswordSuccessView', 'UserResetPasswordSuccessView',
    'UserResetPasswordView', 'UserForgotPasswordView', 'UserFirstLoginView',
]


class UserLoginView(RedirectView):
    url = reverse_lazy('authentication:login')
    query_string = True


class UserForgotPasswordView(FormView):
    template_name = 'users/forgot_password.html'
    form_class = forms.UserForgotPasswordForm

    def form_valid(self, form):
        request = self.request
        email = form.cleaned_data['email']
        user = get_object_or_none(User, email=email)
        if not user:
            error = _('Email address invalid, please input again')
            form.add_error('email', error)
            return self.form_invalid(form)
        elif not user.can_update_password():
            error = _('User auth from {}, go there change password')
            form.add_error('email', error.format(user.get_source_display()))
            return self.form_invalid(form)
        else:
            send_reset_password_mail(user)
            return redirect('authentication:forgot-password-sendmail-success')


class UserForgotPasswordSendmailSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Send reset password message'),
            'messages': _('Send reset password mail success, '
                          'login your mail box and follow it '),
            'redirect_url': reverse('authentication:login'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserResetPasswordSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Reset password success'),
            'messages': _('Reset password success, return to login page'),
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


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

        user.reset_password(password)
        User.expired_reset_password_token(token)
        return redirect('authentication:reset-password-success')


class UserFirstLoginView(PermissionsMixin, TemplateView):
    template_name = 'users/first_login.html'
    permission_classes = [IsValidUser]
