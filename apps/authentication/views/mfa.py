# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
from django.views.generic.edit import FormView
from .. import forms, errors, mixins
from .utils import redirect_to_guard_view

__all__ = ['UserLoginOtpView']


class UserLoginOtpView(mixins.AuthMixin, FormView):
    template_name = 'authentication/login_otp.html'
    form_class = forms.UserCheckOtpCodeForm
    redirect_field_name = 'next'

    def form_valid(self, form):
        otp_code = form.cleaned_data.get('otp_code')
        try:
            self.check_user_mfa(otp_code)
            return redirect_to_guard_view()
        except errors.MFAFailedError as e:
            form.add_error('otp_code', e.msg)
            return super().form_invalid(form)

