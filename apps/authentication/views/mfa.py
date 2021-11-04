# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
from django.views.generic.edit import FormView
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .. import forms, errors, mixins
from .utils import redirect_to_guard_view

from common.utils import get_logger

logger = get_logger(__name__)
__all__ = ['UserLoginOtpView']


class UserLoginOtpView(mixins.AuthMixin, FormView):
    template_name = 'authentication/login_mfa.html'
    form_class = forms.UserCheckOtpCodeForm
    redirect_field_name = 'next'

    def form_valid(self, form):
        code = form.cleaned_data.get('code')
        mfa_type = form.cleaned_data.get('mfa_type')

        try:
            self.check_user_mfa(code, mfa_type)
            return redirect_to_guard_view()
        except (errors.MFAFailedError, errors.BlockMFAError) as e:
            form.add_error('code', e.msg)
            return super().form_invalid(form)
        except Exception as e:
            logger.error(e)
            import traceback
            traceback.print_exc()
            return redirect_to_guard_view()

    def get_context_data(self, **kwargs):
        user = self.get_user_from_session()
        methods = self.get_user_mfa_methods(user)
        kwargs.update({'methods': methods})
        return kwargs
