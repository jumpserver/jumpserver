# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView

from common.utils import get_logger
from users.views import UserFaceCaptureView
from .utils import redirect_to_guard_view
from .. import forms, errors, mixins
from ..const import MFAType, OTP_BIND_AFTER_MFA_SESSION_KEY
from ..services.radius_push import ACTIVE_STATUSES, RadiusPushAttempt, user_can_use_radius_push

logger = get_logger(__name__)
__all__ = ['UserLoginMFAView', 'UserLoginMFAFaceView', 'UserLoginRadiusPushView']


def _otp_enable_url(request):
    url = reverse('authentication:user-otp-enable-start')
    query = request.GET.urlencode()
    return f'{url}?{query}' if query else url


def _mfa_success_redirect(request):
    if request.session.pop(OTP_BIND_AFTER_MFA_SESSION_KEY, None):
        return redirect(_otp_enable_url(request))
    return redirect_to_guard_view('mfa_ok', request.GET.urlencode())


def _radius_push_attempt(request, user):
    if user_can_use_radius_push(user):
        return RadiusPushAttempt.for_session(request.session, user)
    return None


class UserLoginMFAView(mixins.AuthMixin, FormView):
    template_name = 'authentication/login_mfa.html'
    form_class = forms.UserCheckOtpCodeForm
    redirect_field_name = 'next'

    def get(self, *args, **kwargs):
        try:
            user = self.get_user_from_session()
        except errors.SessionEmptyError:
            return redirect_to_guard_view('session_empty')

        try:
            self._check_if_no_active_mfa(user)
        except errors.MFAUnsetError as e:
            return redirect(e.url)

        return super().get(*args, **kwargs)

    @staticmethod
    def _has_active_mfa_except_otp(user):
        return any(
            backend.name != MFAType.OTP.value
            for backend in user.active_mfa_backends
        )

    @staticmethod
    def _is_inactive_otp(user, mfa_type):
        if mfa_type != MFAType.OTP:
            return False
        otp_backend = user.get_mfa_backend_by_type(MFAType.OTP.value)
        return otp_backend and not otp_backend.is_active()

    def _handle_inactive_otp(self, form, user):
        self.request.session[OTP_BIND_AFTER_MFA_SESSION_KEY] = 1
        if not self._has_active_mfa_except_otp(user):
            return redirect(_otp_enable_url(self.request))

        form.add_error(
            'code',
            _('Please verify an active MFA before binding OTP.')
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        code = form.cleaned_data.get('code')
        mfa_type = form.cleaned_data.get('mfa_type')
        try:
            user = self.get_user_from_session()
        except errors.SessionEmptyError:
            return redirect_to_guard_view('session_empty')

        attempt = _radius_push_attempt(self.request, user)
        if attempt:
            if mfa_type == MFAType.Radius:
                form.add_error('code', _('Use Send push to verify your sign-in.'))
                return super().form_invalid(form)
            attempt.cancel()

        if self._is_inactive_otp(user, mfa_type):
            return self._handle_inactive_otp(form, user)

        if mfa_type == MFAType.Face:
            return redirect(reverse('authentication:login-face-capture'))
        elif mfa_type == MFAType.Passkey:
            return redirect('/api/v1/authentication/passkeys/login/')
        return self.do_mfa_check(form, code, mfa_type)

    def do_mfa_check(self, form, code, mfa_type):
        from users.utils import MFABlockUtils

        try:
            self._do_check_user_mfa(code, mfa_type)
            user, ip = self.get_user_from_session(), self.get_request_ip()
            MFABlockUtils(user.username, ip).clean_failed_count()
            return _mfa_success_redirect(self.request)
        except (errors.MFAFailedError, errors.BlockMFAError) as e:
            form.add_error('code', e.msg)
            return super().form_invalid(form)
        except errors.SessionEmptyError:
            return redirect_to_guard_view('session_empty')
        except Exception as e:
            logger.error(e)
            import traceback
            traceback.print_exc()
            return redirect_to_guard_view('unexpect')

    def get_context_data(self, **kwargs):
        user = self.get_user_from_session()
        mfa_context = self.get_user_mfa_context(user)
        kwargs.update(mfa_context)
        attempt = _radius_push_attempt(self.request, user)
        kwargs['radius_push_enabled'] = attempt is not None
        current = attempt.get() if attempt else None
        if current and current['status'] in ACTIVE_STATUSES:
            kwargs['radius_push_attempt_id'] = current['id']
        return kwargs


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginRadiusPushView(mixins.AuthMixin, View):
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        try:
            self.push_user = self.get_user_from_session()
        except errors.SessionEmptyError:
            return JsonResponse({'status': 'session_expired'}, status=401)
        self.push_attempt = _radius_push_attempt(request, self.push_user)
        if self.push_attempt is None:
            return JsonResponse({'status': 'unavailable'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _response(attempt, fallback='unavailable'):
        if not attempt:
            return JsonResponse({'status': fallback})
        status = 'pending' if attempt['status'] == 'queued' else attempt['status']
        return JsonResponse({'status': status, 'attempt': attempt['id']})

    def get(self, request):
        attempt_id = request.GET.get('attempt')
        return self._response(self.push_attempt.get(attempt_id) if attempt_id else None)

    def post(self, request):
        action = request.POST.get('action')
        attempt_id = request.POST.get('attempt')
        if action == 'cancel' and attempt_id:
            return self._response(self.push_attempt.cancel(attempt_id), 'cancelled')
        if self.request.session.get('auth_mfa') and (
            self.request.session.get('auth_mfa_username') == self.push_user.username
        ):
            return self._complete_response()
        try:
            self.check_mfa_is_block(self.push_user.username, self.get_request_ip())
        except errors.BlockMFAError as exc:
            return JsonResponse({'status': 'blocked', 'message': exc.msg}, status=403)
        if action == 'start':
            return self._start()
        if action == 'complete' and attempt_id:
            attempt = self.push_attempt.transition(attempt_id, {'approved'}, 'consumed')
            if attempt:
                self.mark_mfa_ok(MFAType.Radius.value, self.push_user)
                return self._complete_response()
            return self._response(self.push_attempt.get(attempt_id))
        return JsonResponse({'status': 'unavailable'}, status=400)

    def _start(self):
        from ..tasks import authenticate_radius_push

        attempt, created = self.push_attempt.start(
            self.push_user, self.get_request_ip(), self.request.session['auth_password_expired_at'],
        )
        if created:
            try:
                authenticate_radius_push.apply_async(
                    args=(self.push_attempt.key, attempt['id']),
                    expires=int(settings.RADIUS_PUSH_TIMEOUT), retry=False,
                )
            except Exception:
                logger.exception('Could not queue RADIUS push request')
                self.push_attempt.transition(attempt['id'], {'queued'}, 'failed')
                return JsonResponse({'status': 'failed'}, status=503)
        return self._response(attempt, 'rate_limited')

    def _complete_response(self):
        return JsonResponse({'status': 'complete', 'redirect': _mfa_success_redirect(self.request).url})


class UserLoginMFAFaceView(UserFaceCaptureView, UserLoginMFAView):
    def form_valid(self, form):
        return self.do_mfa_check(form, self.code, self.mfa_type)
