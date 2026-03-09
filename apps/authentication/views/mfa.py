# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.shortcuts import redirect, reverse
from django.views.generic.edit import FormView

from common.utils import get_logger
from users.views import UserFaceCaptureView
from .utils import redirect_to_guard_view
from .. import forms, errors, mixins
from ..const import MFAType

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

    def form_valid(self, form):
        code = form.cleaned_data.get('code')
        mfa_type = form.cleaned_data.get('mfa_type')

        if mfa_type == MFAType.Face:
            return redirect(reverse('authentication:login-face-capture'))
        elif mfa_type == MFAType.Passkey:
            return redirect('/api/v1/authentication/passkeys/login/')
        
        # 特殊处理：如果选择 OTP 且未配置，直接跳转到设置页面
        if mfa_type == 'otp':
            user = self.get_user_from_session()
            mfa_backend = user.get_mfa_backend_by_type(mfa_type)
            if mfa_backend and hasattr(mfa_backend, 'is_configured'):
                if not mfa_backend.is_configured():
                    set_url = mfa_backend.get_enable_url()
                    return redirect(set_url + '?_=login_mfa')
        
        return self.do_mfa_check(form, code, mfa_type)

    def do_mfa_check(self, form, code, mfa_type):
        from users.utils import MFABlockUtils

        try:
            self._do_check_user_mfa(code, mfa_type)
            user, ip = self.get_user_from_session(), self.get_request_ip()
            MFABlockUtils(user.username, ip).clean_failed_count()
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
        
        # 检查是否需要显示 OTP 设置提示
        # 只有在有多个 MFA 选项且 OTP 未配置时才显示
        mfa_backends = mfa_context.get('mfa_backends', [])
        show_otp_hint = False
        
        if len(mfa_backends) > 1:  # 有多个 MFA 选项
            for backend in mfa_backends:
                if backend.name == 'otp':
                    if hasattr(backend, 'is_configured'):
                        show_otp_hint = not backend.is_configured()
                    else:
                        show_otp_hint = not backend.is_active()
                    break
        
        kwargs.update(mfa_context)
        kwargs['show_otp_hint'] = show_otp_hint
        return kwargs
        return kwargs


class UserLoginMFAFaceView(UserFaceCaptureView, UserLoginMFAView):
    def form_valid(self, form):
        return self.do_mfa_check(form, self.code, self.mfa_type)
