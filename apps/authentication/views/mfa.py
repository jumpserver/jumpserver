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
    template_name = 'authentication/login_otp.html'
    form_class = forms.UserCheckOtpCodeForm
    redirect_field_name = 'next'

    def form_valid(self, form):
        otp_code = form.cleaned_data.get('code')
        mfa_type = form.cleaned_data.get('mfa_type')

        try:
            self.check_user_mfa(otp_code, mfa_type)
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
        context = {
            'methods': [
                {
                    'name': 'otp',
                    'label': _('One-time password'),
                    'enable': bool(user.otp_secret_key),
                    'selected': False,
                },
                {
                    'name': 'sms',
                    'label': _('SMS'),
                    'enable': bool(user.phone) and settings.SMS_ENABLED and settings.XPACK_ENABLED,
                    'selected': False,
                },
            ]
        }

        for item in context['methods']:
            if item['enable']:
                item['selected'] = True
                break
        context.update(kwargs)
        return context
