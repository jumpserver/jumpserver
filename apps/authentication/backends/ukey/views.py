# -*- coding: utf-8 -*-
#
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import FormView
from django.shortcuts import redirect

from authentication.mixins import AuthMixin 
from authentication.errors import (
    AuthFailedError, NeedRedirectError
)
from .forms import UKeyLoginForm
from users.utils import LoginBlockUtil, LoginIpBlockUtil
from .sdk import ukey_sdk_config


__all__ = ['UKeyLoginView']

_CHALLENGE_CACHE_KEY_PREFIX = 'ukey_login_challenge'
_UKEY_ERROR_SESSION_KEY = 'ukey_login_error'

@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UKeyLoginView(AuthMixin, FormView):
    template_name = 'authentication/login_ukey.html'
    form_class = UKeyLoginForm
    redirect_field_name = 'next'

    # ------------------------------------------------------------------
    # Challenge helpers
    # ------------------------------------------------------------------

    def _ensure_session(self):
        if not self.request.session.session_key:
            self.request.session.create()

    def _challenge_cache_key(self):
        self._ensure_session()
        return f'{_CHALLENGE_CACHE_KEY_PREFIX}_{self.request.session.session_key}'

    def _generate_and_store_challenge(self):
        challenge = secrets.token_hex(16)
        ttl = ukey_sdk_config.challenge_ttl
        cache.set(self._challenge_cache_key(), challenge, ttl)
        return challenge

    def _get_stored_challenge(self):
        return cache.get(self._challenge_cache_key(), '')

    def _delete_stored_challenge(self):
        cache.delete(self._challenge_cache_key())

    def _get_next_url(self):
        next = self.request.GET.get(self.redirect_field_name)
        next = next or self.request.POST.get(self.redirect_field_name)
        return next

    def _build_login_redirect_url(self):
        next_url = self._get_next_url()
        if not next_url:
            return self.request.path
        query = urlencode({self.redirect_field_name: next_url})
        return f'{self.request.path}?{query}'

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['challenge'] = self._generate_and_store_challenge()
        context['error_msg'] = self.request.session.pop(_UKEY_ERROR_SESSION_KEY, '')
        return context

    def form_valid(self, form):
        username  = form.cleaned_data['username']
        cert      = form.cleaned_data['cert']
        signature = form.cleaned_data['signature']
        ukey_sn   = form.cleaned_data['ukey_sn']

        challenge = self._get_stored_challenge()
        if not challenge:
            error = _('Authentication challenge expired, please refresh the page and try again.')
            return self.get_failed_response(form, username, error)

        error_msg = None
        ip = self.get_request_ip()

        try:
            self._check_is_block(username, True)
            self._check_only_allow_exists_user_auth(username)

            user = authenticate(
                self.request, username=username, cert=cert, signature=signature,
                challenge=challenge, ukey_sn=ukey_sn,
            )
            if user is None:
                error_msg = getattr(self.request, 'error_message', None) or _('Invalid credentials')
                return self.get_failed_response(form, username, error_msg)

            username = user.username
            self._check_login_acl(user, ip)

            LoginIpBlockUtil(ip).clean_block_if_need()
            LoginBlockUtil(username, ip).clean_failed_count()
        except AuthFailedError as e:
            error_msg = e.msg
        except NeedRedirectError as e:
            return redirect(e.url)
        except Exception as e:
            error_msg = str(e)
        finally:
            self._delete_stored_challenge()

        if error_msg:
            return self.get_failed_response(form, username, error_msg)
        else:
            return self.get_success_response(self.request, user)

    def form_invalid(self, form):
        error_msg = self._get_form_error_message(form)
        username = (form.data.get('username') or '').strip()
        return self.get_failed_response(form, username, error_msg)

    @staticmethod
    def _get_form_error_message(form):
        non_field_errors = list(form.non_field_errors())
        if non_field_errors:
            return ' '.join(non_field_errors)

        field_errors = []
        for field_name, errors in form.errors.items():
            if field_name == '__all__':
                continue
            field_label = UKeyLoginView._get_field_label(form, field_name)
            field_errors.append(f"{field_label}: {' '.join(errors)}")
        if field_errors:
            return ' '.join(field_errors)
        return _('Unknown')

    @staticmethod
    def _get_field_label(form, field_name):
        field = form.fields.get(field_name)
        if field and field.label:
            return field.label
        return field_name

    def get_failed_response(self, form, username, error_msg):
        self.request.session[_UKEY_ERROR_SESSION_KEY] = str(error_msg or _('Unknown'))
        self.send_auth_signal(success=False, reason=error_msg, username=username)
        return redirect(self._build_login_redirect_url())
    
    def get_success_response(self, request, user):
        self.mark_ukey_ok(user, auth_backend=settings.AUTH_BACKEND_UKEY)
        if not settings.SAFE_MODE:
            self.mark_mfa_ok('ukey-pass-mfa', user)
        return self.redirect_to_guard_view()

