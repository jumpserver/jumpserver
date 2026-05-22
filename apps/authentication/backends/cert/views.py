# -*- coding: utf-8 -*-
#
import secrets

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import FormView
from django.shortcuts import redirect
from django.http.response import HttpResponseRedirect

from common.utils import reverse, safe_next_url
from users.utils import redirect_user_first_login_or_index
from authentication.mixins import AuthMixin 
from authentication.errors import ACLError
from authentication.errors import (
    AuthFailedError, LoginConfirmBaseError, NeedRedirectError
)
from .forms import CertLoginForm
from users.utils import LoginBlockUtil, LoginIpBlockUtil


__all__ = ['CertLoginView']

_CHALLENGE_CACHE_KEY_PREFIX = 'cert_login_challenge'
NEXT_URL = 'next'

@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CertLoginView(AuthMixin, FormView):
    template_name = 'authentication/cert_login.html'
    form_class = CertLoginForm
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
        ttl = getattr(settings, 'AUTH_CERT_CHALLENGE_TTL', 300)
        cache.set(self._challenge_cache_key(), challenge, ttl)
        return challenge

    def _get_stored_challenge(self):
        return cache.get(self._challenge_cache_key(), '')

    def _delete_stored_challenge(self):
        cache.delete(self._challenge_cache_key())

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------

    def get(self, request, *args, **kwargs):
        challenge = self._generate_and_store_challenge()
        context = self.get_context_data(form=self.get_form(), challenge=challenge)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'challenge' not in context:
            context['challenge'] = self._get_stored_challenge()
        return context

    def form_valid(self, form):
        username  = form.cleaned_data['username']
        cert      = form.cleaned_data['cert']
        signature = form.cleaned_data['signature']
        challenge = self._get_stored_challenge()

        error_msg = None
        ip = self.get_request_ip()

        try:
            self._check_is_block(username, True)
            self._check_only_allow_exists_user_auth(username)

            user = authenticate(
                self.request, username=username, cert=cert, signature=signature, challenge=challenge
            )
            if user is None:
                error_msg = _('Invalid credentials')
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
    
    def get_failed_response(self, form, username, error_msg):
        form.add_error(None, error_msg)
        # Refresh the challenge so it cannot be replayed
        challenge = self._generate_and_store_challenge()
        context = self.get_context_data(form=form, challenge=challenge)
        self.send_auth_signal(success=False, reason=error_msg, username=username)
        return self.render_to_response(context)
    
    def get_success_response(self, request, user):
        self.mark_cert_ok(user, auth_backend=settings.AUTH_BACKEND_CERT)
        return self.redirect_to_guard_view()
