# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.shortcuts import redirect, reverse
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView

from common.utils import get_logger
from users.views import UserFaceCaptureView
from .utils import redirect_to_guard_view
from .. import forms, errors, mixins
from ..const import MFAType, OTP_BIND_AFTER_MFA_SESSION_KEY
from ..mfa.radius_push import MFARadiusPush
from ..services.radius_push import ACTIVE_STATUSES

logger = get_logger(__name__)
__all__ = ['UserLoginMFAView', 'UserLoginMFAFaceView']


def _otp_enable_url(request):
    url = reverse('authentication:user-otp-enable-start')
    query = request.GET.urlencode()
    return f'{url}?{query}' if query else url


def _mfa_success_redirect(request):
    if request.session.pop(OTP_BIND_AFTER_MFA_SESSION_KEY, None):
        return redirect(_otp_enable_url(request))
    return redirect_to_guard_view('mfa_ok', request.GET.urlencode())


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
            self._check_if_no_active_mfa(
                user, include_web_login_only=MFARadiusPush.login_attempt(self.request, user) is not None,
            )
        except errors.MFAUnsetError as e:
            return redirect(e.url)

        return super().get(*args, **kwargs)

    def _has_active_mfa_except_otp(self, user):
        push_available = MFARadiusPush.login_attempt(self.request, user) is not None
        return any(name != MFAType.OTP.value for name in self._active_mfa_names(user, push_available))

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

        if mfa_type == MFAType.RadiusPush:
            form.add_error('code', _('Use Send push to verify your sign-in.'))
            return super().form_invalid(form)

        attempt = MFARadiusPush.login_attempt(self.request, user)
        if attempt:
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
        attempt = MFARadiusPush.login_attempt(self.request, user)
        kwargs['radius_push_available'] = attempt is not None
        if not attempt:
            kwargs['mfa_backends'] = [
                backend for backend in kwargs['mfa_backends'] if not backend.web_login_only
            ]
        current = attempt.get() if attempt else None
        if current and current['status'] in ACTIVE_STATUSES:
            kwargs['radius_push_attempt_id'] = current['id']
        return kwargs


class UserLoginMFAFaceView(UserFaceCaptureView, UserLoginMFAView):
    def form_valid(self, form):
        return self.do_mfa_check(form, self.code, self.mfa_type)
