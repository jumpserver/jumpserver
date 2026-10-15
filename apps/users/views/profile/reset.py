# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import login
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, reverse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import FormView, RedirectView

from authentication.const import CUSTOM_SSO_FIRST_LOGIN_SESSION_KEY
from authentication import password_reset
from authentication.signals import post_auth_success
from common.const.choices import COUNTRY_CALLING_CODES
from common.utils import FlashMessageUtil, safe_next_url
from users.notifications import ResetPasswordSuccessMsg
from ... import forms
from ...models import User
from ...utils import check_password_rules, get_password_check_rules

__all__ = [
    'UserLoginView',
    'UserResetPasswordView',
    'UserForgotPasswordView',
    'UserForgotPasswordPreviewingView',
]


class UserLoginView(RedirectView):
    url = reverse_lazy('authentication:login')
    query_string = True


class PasswordRecoveryHeadersMixin:
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response


class UserForgotPasswordPreviewingView(PasswordRecoveryHeadersMixin, FormView):
    template_name = 'users/forgot_password_previewing.html'
    form_class = forms.UserForgotPasswordPreviewingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.session.pop('password_recovery_expired', False):
            context['errors'] = _('This page has expired. Please start again.')
        return context

    def form_valid(self, form):
        try:
            token = password_reset.issue(self.request, form.cleaned_data['username'])
        except password_reset.RecoveryThrottled as exc:
            form.add_error(None, str(exc))
            response = self.form_invalid(form)
            response.status_code = 429
            response['Retry-After'] = str(exc.wait)
            return response
        return redirect(reverse('authentication:forgot-password') + '?token=' + token)


class UserForgotPasswordView(PasswordRecoveryHeadersMixin, FormView):
    template_name = 'users/forgot_password.html'
    form_class = forms.UserForgotPasswordForm

    def dispatch(self, request, *args, **kwargs):
        self.token = request.GET.get('token')
        self.flow = password_reset.get_flow(request, self.token)
        if not self.flow:
            request.session['password_recovery_expired'] = True
            response = redirect(reverse('authentication:forgot-previewing'))
            response['Cache-Control'] = 'no-store'
            response['Referrer-Policy'] = 'no-referrer'
            return response
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        data = getattr(context['form'], 'cleaned_data', {})
        context.update({k: v for k, v in data.items() if k in ('email', 'sms', 'country_code')})
        context['countries'] = COUNTRY_CALLING_CODES
        context['form_type'] = data.get('form_type', 'email')
        backends = [{'name': _('Email'), 'is_active': True, 'value': 'email'}]
        if settings.XPACK_LICENSE_IS_VALID:
            backends.append({'name': _('SMS'), 'is_active': settings.SMS_ENABLED, 'value': 'sms'})
        context['validate_backends'] = backends
        return context

    def form_valid(self, form):
        form_type = form.cleaned_data['form_type']
        target = form.cleaned_data[form_type]
        if form_type == 'sms':
            target = form.cleaned_data['country_code'] + target
        try:
            user = password_reset.verify(
                self.request, self.token, self.flow, form_type, target, form.cleaned_data['code']
            )
        except password_reset.RecoveryError as exc:
            form.add_error('code', str(exc))
            response = self.form_invalid(form)
            if isinstance(exc, password_reset.RecoveryThrottled):
                response.status_code = 429
                response['Retry-After'] = str(exc.wait)
            return response
        token = user.generate_reset_token(for_password_reset=True)
        return redirect(reverse('authentication:reset-password') + '?token=' + token)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class UserResetPasswordView(PasswordRecoveryHeadersMixin, FormView):
    template_name = 'users/reset_password.html'
    form_class = forms.UserTokenResetPasswordForm

    def dispatch(self, request, *args, **kwargs):
        # Own the transaction so the recovery lock encloses the actual commit,
        # rather than being released before ATOMIC_REQUESTS commits the response.
        token = request.GET.get('token') if request.method == 'POST' else None
        with password_reset.reset_token_lock(token) as self.is_password_recovery, transaction.atomic():
            return super().dispatch(request, *args, **kwargs)

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
        else:
            check_rules = get_password_check_rules(user)
            context['password_check_rules'] = check_rules
        return context

    def form_valid(self, form):
        token = self.request.GET.get('token')
        user = User.validate_reset_password_token(token)
        if not user:
            error = _('Token invalid or expired')
            form.add_error('new_password', error)
            return self.form_invalid(form)

        pending = self.request.session.get(CUSTOM_SSO_FIRST_LOGIN_SESSION_KEY) or {}
        is_custom_sso_first_login = pending.get('token') == token
        if is_custom_sso_first_login and (
            not settings.AUTH_CUSTOM_SSO or
            pending.get('user_id') != str(user.id) or
            not user.is_valid or not user.is_first_login
        ):
            return HttpResponseForbidden()

        if not user.can_update_password():
            error = _('User auth from {}, go there change password')
            form.add_error('new_password', error.format(user.get_source_display()))
            return self.form_invalid(form)

        password = form.cleaned_data['new_password']
        if is_custom_sso_first_login and user.check_password(password):
            form.add_error('new_password', _('The new password must differ from the current password'))
            return self.form_invalid(form)

        is_ok = check_password_rules(password, is_org_admin=user.is_org_admin)
        if not is_ok:
            error = _('* Your password does not meet the requirements')
            form.add_error('new_password', error)
            return self.form_invalid(form)

        if user.is_history_password(password):
            limit_count = settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT
            error = _('* The new password cannot be the last {} passwords').format(
                limit_count
            )
            form.add_error('new_password', error)
            return self.form_invalid(form)

        if user.check_leak_password(password):
            error = _('Your password is too simple, please change it for security')
            form.add_error('new_password', error)
            return self.form_invalid(form)

        user.reset_password(password)
        if self.is_password_recovery:
            transaction.on_commit(lambda: User.expired_reset_password_token(token), robust=True)
        else:
            User.expired_reset_password_token(token)

        ResetPasswordSuccessMsg(user, self.request).publish_async()
        if is_custom_sso_first_login:
            user.is_first_login = False
            user.save(update_fields=['is_first_login'])

            login(self.request, user, backend=settings.AUTH_BACKEND_CUSTOM_SSO)
            self.request.session.pop(CUSTOM_SSO_FIRST_LOGIN_SESSION_KEY, None)
            post_auth_success.send(sender=self.__class__, user=user, request=self.request)
            return redirect(safe_next_url(pending.get('next_url'), request=self.request))

        return redirect(self.get_redirect_url())

    @staticmethod
    def get_redirect_url():
        message_data = {
            'title': _('Reset password success'),
            'message': _('Password reset successfully. Please log in again.'),
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        return FlashMessageUtil.gen_message_url(message_data)
