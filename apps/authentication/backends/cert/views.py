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

from users.utils import redirect_user_first_login_or_index
from .forms import CertLoginForm


__all__ = ['CertLoginView']

_CHALLENGE_CACHE_KEY_PREFIX = 'cert_login_challenge'


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class CertLoginView(FormView):
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

        user = authenticate(self.request, username=username, cert=cert, signature=signature, challenge=challenge)
        if user is None:
            form.add_error(None, _('Authentication failed'))
            # Refresh the challenge so it cannot be replayed
            challenge = self._generate_and_store_challenge()
            context = self.get_context_data(form=form, challenge=challenge)
            return self.render_to_response(context)

        self._delete_stored_challenge()
        auth_login(self.request, user)
        redirect_url = redirect_user_first_login_or_index(self.request, self.redirect_field_name)
        return redirect(redirect_url)
