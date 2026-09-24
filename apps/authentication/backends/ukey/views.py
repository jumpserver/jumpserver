# -*- coding: utf-8 -*-
#
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
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
from .forms import CertificateUKeyLoginForm, UKeyLoginForm
from users.utils import LoginBlockUtil, LoginIpBlockUtil
from . import challenges
from .binding import binding_version
from .configuration import ensure_enabled, get_snapshot, locked_snapshot
from .exceptions import UKeyAuthError, UKeyServiceError
from .pending import clear_pending_auth
from .providers import get_provider


__all__ = ['UKeyLoginView']

_UKEY_ERROR_SESSION_KEY = 'ukey_login_error'
_CHALLENGE_CACHE_KEY_PREFIX = 'ukey_login_challenge'

@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UKeyLoginView(AuthMixin, FormView):
    template_name = 'authentication/login_ukey.html'
    form_class = UKeyLoginForm
    redirect_field_name = 'next'

    @cached_property
    def provider(self):
        return get_provider(get_snapshot())

    def get_form_class(self):
        if self.provider.binding_mode == 'certificate':
            return CertificateUKeyLoginForm
        return UKeyLoginForm

    def dispatch(self, request, *args, **kwargs):
        # OIDC/CAS may have logged in while MFA or approval is still pending.
        if self.provider.binding_mode == 'certificate' and request.user.is_authenticated:
            return self.redirect_to_guard_view()
        return super().dispatch(request, *args, **kwargs)

    def _challenge_cache_key(self):
        if not self.request.session.session_key:
            self.request.session.create()
        return f'{_CHALLENGE_CACHE_KEY_PREFIX}_{self.request.session.session_key}'

    def _generate_and_store_challenge(self):
        challenge = secrets.token_hex(16)
        ttl = int(self.provider.snapshot['AUTH_UKEY_CHALLENGE_TTL'])
        cache.set(self._challenge_cache_key(), challenge, ttl)
        return challenge

    def _get_stored_challenge(self):
        return cache.get(self._challenge_cache_key(), '')

    def _delete_stored_challenge(self):
        cache.delete(self._challenge_cache_key())

    def _clear_pending_auth(self):
        # Preserve the builtin lifecycle; only discard external-provider state
        # when leaving it, or all prior state when starting an external proof.
        if self.provider.binding_mode == 'certificate' or 'auth_ukey_state' in self.request.session:
            clear_pending_auth(self.request)

    # ------------------------------------------------------------------
    # Redirect helpers
    # ------------------------------------------------------------------

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
        self._clear_pending_auth()
        if self.provider.binding_mode != 'certificate':
            context['challenge'] = self._generate_and_store_challenge()
            context['ukey_provider'] = self.provider.id
            context['error_msg'] = self.request.session.pop(_UKEY_ERROR_SESSION_KEY, '')
            return context
        context['error_msg'] = self.request.session.pop(_UKEY_ERROR_SESSION_KEY, '')
        try:
            self._check_is_block('', True)
            issued = challenges.issue(self.request, 'login')
            context.update(challenge=issued['code'], challenge_id=issued['id'],
                           ukey_revision=issued['revision'], ukey_provider=issued['provider'])
        except UKeyServiceError as exc:
            # Do not hide an earlier proof error if obtaining the next challenge fails.
            context['error_msg'] = context['error_msg'] or str(exc)
        except (UKeyAuthError, AuthFailedError):
            context['error_msg'] = _('UKey login is temporarily unavailable. Try again later or use another login method.')
        return context

    def form_valid(self, form):
        self._clear_pending_auth()
        certificate_binding = self.provider.binding_mode == 'certificate'
        username  = form.cleaned_data['username']
        cert      = form.cleaned_data['cert']
        signature = form.cleaned_data['signature']
        ukey_sn   = form.cleaned_data['ukey_sn']

        if not certificate_binding:
            challenge = self._get_stored_challenge()
            if not challenge:
                error = _('Authentication challenge expired, please refresh the page and try again.')
                return self.get_failed_response(form, username, error)

        error_msg = None
        ip = self.get_request_ip()
        try:
            if certificate_binding:
                username = ''
            self._check_is_block(username, True)
            if not certificate_binding:
                self._check_only_allow_exists_user_auth(username)

            proof = {'cert': cert, 'signature': signature, 'ukey_sn': ukey_sn}
            if certificate_binding:
                proof['challenge_id'] = form.cleaned_data['challenge_id']
            else:
                proof['challenge'] = challenge
            # Django masks credential keys containing "key" when emitting
            # user_login_failed; never expose certificate/signature payloads there.
            user = authenticate(self.request, username=username, ukey_proof=proof)
            if user is None:
                error_msg = getattr(self.request, 'error_message', None) or _('Invalid credentials')
                return self.get_failed_response(form, username, error_msg)

            username = user.username
            # For external certificates, apply account restrictions only after
            # verified binding resolution. Client CN/username is not an identity.
            if certificate_binding:
                self._check_is_block(username, True)
                self._check_only_allow_exists_user_auth(username)
            self._check_login_acl(user, ip)

            LoginIpBlockUtil(ip).clean_block_if_need()
            LoginBlockUtil(username, ip).clean_failed_count()
            if certificate_binding:
                return self.get_success_response(self.request, user)
        except AuthFailedError as e:
            error_msg = e.msg
        except NeedRedirectError as e:
            return redirect(e.url)
        except Exception as e:
            error_msg = str(e)
        finally:
            if not certificate_binding:
                self._delete_stored_challenge()
        if error_msg:
            return self.get_failed_response(form, username, error_msg)
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
        self._clear_pending_auth()
        self.request.session[_UKEY_ERROR_SESSION_KEY] = str(error_msg or _('Unknown'))
        self.send_auth_signal(success=False, reason=error_msg, username=username)
        return redirect(self._build_login_redirect_url())
    
    def get_success_response(self, request, user):
        if self.provider.binding_mode != 'certificate':
            request.session.pop('auth_ukey_state', None)
            self.mark_ukey_ok(user, auth_backend=settings.AUTH_BACKEND_UKEY)
            if not settings.SAFE_MODE:
                self.mark_mfa_ok('ukey-pass-mfa', user)
            return self.redirect_to_guard_view()

        from users.models import User
        from .backends import UKeyBackend
        with locked_snapshot(request.ukey_auth_state['revision']) as snapshot:
            provider = ensure_enabled(snapshot, request.ukey_auth_state['provider'])
            user = User.objects.select_for_update().get(pk=user.pk)
            if binding_version(user.pk, provider.id) != getattr(request, 'ukey_binding_version', None):
                raise UKeyAuthError('Certificate binding changed; refresh and retry')
            backend = UKeyBackend()
            if not backend.user_can_authenticate(user) or not backend.user_allow_authenticate(user):
                raise UKeyAuthError('User is not allowed to authenticate with UKey')
            self.mark_ukey_ok(user, auth_backend=settings.AUTH_BACKEND_UKEY)
            request.session['auth_ukey_state'] = {
                **request.ukey_auth_state, 'user_id': str(user.pk),
                'binding_version': getattr(request, 'ukey_binding_version', ''),
            }
            if not settings.SAFE_MODE:
                self.mark_mfa_ok('ukey-pass-mfa', user)
            return self.redirect_to_guard_view()
