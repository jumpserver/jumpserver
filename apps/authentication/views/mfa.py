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

logger = get_logger(__name__)
__all__ = ['UserLoginMFAView', 'UserLoginMFAFaceView']


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
            return redirect(e.url + '?_=login_mfa')

        return super().get(*args, **kwargs)

    def _get_otp_enable_url(self):
        url = reverse('authentication:user-otp-enable-start')
        query_string = self.request.GET.urlencode()
        if query_string:
            url = f'{url}?{query_string}'
        return url

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
            return redirect(self._get_otp_enable_url())

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
            if self.request.session.pop(OTP_BIND_AFTER_MFA_SESSION_KEY, None):
                return redirect(self._get_otp_enable_url())

            query_string = self.request.GET.urlencode()
            return redirect_to_guard_view('mfa_ok', query_string)
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
        return kwargs


class UserLoginMFAFaceView(UserFaceCaptureView, UserLoginMFAView):
    def form_valid(self, form):
        return self.do_mfa_check(form, self.code, self.mfa_type)
