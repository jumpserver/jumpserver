# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

import time

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect, reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import FormView, RedirectView

from authentication.errors import IntervalTooShort
from authentication.utils import check_user_property_is_correct
from common.const.choices import COUNTRY_CALLING_CODES
from common.utils import FlashMessageUtil, get_object_or_none, random_string
from common.utils.verify_code import SendAndVerifyCodeUtil
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


class UserForgotPasswordPreviewingView(FormView):
    template_name = 'users/forgot_password_previewing.html'
    form_class = forms.UserForgotPasswordPreviewingForm

    @staticmethod
    def get_redirect_url(token):
        return reverse('authentication:forgot-password') + '?token=%s' % token

    @staticmethod
    def generate_previewing_token(user):
        sent_ttl = 60
        token_sent_at_key = '{}_send_at'.format(user.username)
        token_sent_at = cache.get(token_sent_at_key, 0)

        if token_sent_at:
            raise IntervalTooShort(sent_ttl)
        token = random_string(36)
        user_info = {'username': user.username, 'phone': user.phone, 'email': user.email}
        cache.set(token, user_info, 5 * 60)
        cache.set(token_sent_at_key, time.time(), sent_ttl)
        return token

    def form_valid(self, form):
        username = form.cleaned_data['username']
        user = get_object_or_none(User, username=username)
        if not user:
            form.add_error('username', _('User does not exist: {}').format(username))
            return super().form_invalid(form)
        if settings.ONLY_ALLOW_AUTH_FROM_SOURCE and not user.is_local:
            error = _('Non-local users can log in only from third-party platforms '
                      'and cannot change their passwords: {}').format(username)
            form.add_error('username', error)
            return super().form_invalid(form)

        try:
            token = self.generate_previewing_token(user)
        except IntervalTooShort as e:
            form.add_error('username', e)
            return super().form_invalid(form)
        return redirect(self.get_redirect_url(token))


class UserForgotPasswordView(FormView):
    template_name = 'users/forgot_password.html'
    form_class = forms.UserForgotPasswordForm

    def get(self, request, *args, **kwargs):
        token = self.request.GET.get('token')
        userinfo = cache.get(token)
        if not userinfo:
            return redirect(self.get_redirect_url(return_previewing=True))
        else:
            context = self.get_context_data(has_phone=bool(userinfo['phone']))
            return self.render_to_response(context)

    @staticmethod
    def get_validate_backends_context(has_phone):
        validate_backends = [{'name': _('Email'), 'is_active': True, 'value': 'email'}]
        if settings.XPACK_LICENSE_IS_VALID:
            if settings.SMS_ENABLED and has_phone:
                is_active = True
            else:
                is_active = False
            sms_backend = {'name': _('SMS'), 'is_active': is_active, 'value': 'sms'}
            validate_backends.append(sms_backend)
        return {'validate_backends': validate_backends}

    def get_context_data(self, has_phone=False, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context['form']

        cleaned_data = getattr(form, 'cleaned_data', {})
        for k, v in cleaned_data.items():
            if v:
                context[k] = v
        context['countries'] = COUNTRY_CALLING_CODES
        context['form_type'] = 'email'
        context['XPACK_ENABLED'] = settings.XPACK_ENABLED
        validate_backends = self.get_validate_backends_context(has_phone)
        context.update(validate_backends)
        return context

    @staticmethod
    def get_redirect_url(user=None, return_previewing=False):
        if not user and return_previewing:
            return reverse('authentication:forgot-previewing')
        query_params = '?token=%s' % user.generate_reset_token()
        reset_password_url = reverse('authentication:reset-password')
        return reset_password_url + query_params

    @staticmethod
    def safe_verify_code(token, target, form_type, code):
        token_verified_key = '{}_verified'.format(token)
        token_verified_times = cache.get(token_verified_key, 0)

        if token_verified_times >= 3:
            cache.delete(token)
            raise ValueError('Verification code has been used more than 3 times, please re-verify')
        cache.set(token_verified_key, token_verified_times + 1, 5 * 60)
        sender_util = SendAndVerifyCodeUtil(target, backend=form_type)
        return sender_util.verify(code)

    def form_valid(self, form):
        token = self.request.GET.get('token')
        user_info = cache.get(token)
        if not user_info:
            return redirect(self.get_redirect_url(return_previewing=True))

        username = user_info.get('username')
        form_type = form.cleaned_data['form_type']
        target = form.cleaned_data[form_type]
        code = form.cleaned_data['code']

        query_key = form_type
        if form_type == 'sms':
            query_key = 'phone'

        try:
            self.safe_verify_code(token, target, form_type, code)
        except ValueError as e:
            return redirect(self.get_redirect_url(return_previewing=True))
        except Exception as e:
            form.add_error('code', str(e))
            return super().form_invalid(form)

        user = check_user_property_is_correct(username, **{query_key: target})
        if not user:
            form.add_error('code', _('No user matched'))
            return super().form_invalid(form)

        return redirect(self.get_redirect_url(user))


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

        if not user.can_update_password():
            error = _('User auth from {}, go there change password')
            form.add_error('new_password', error.format(user.get_source_display()))
            return self.form_invalid(form)

        password = form.cleaned_data['new_password']
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

        user.reset_password(password)
        User.expired_reset_password_token(token)

        ResetPasswordSuccessMsg(user, self.request).publish_async()
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
