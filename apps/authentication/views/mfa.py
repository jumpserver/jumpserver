# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
from django.views.generic.edit import FormView
from django.shortcuts import redirect

from common.utils import get_logger
from .. import forms, errors, mixins
from .utils import redirect_to_guard_view

logger = get_logger(__name__)
__all__ = ['UserLoginMFAView']


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
        from users.utils import MFABlockUtils
        code = form.cleaned_data.get('code')
        mfa_type = form.cleaned_data.get('mfa_type')

        try:
            self._do_check_user_mfa(code, mfa_type)
            user, ip = self.get_user_from_session(), self.get_request_ip()
            MFABlockUtils(user.username, ip).clean_failed_count()
            return redirect_to_guard_view('mfa_ok')
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

