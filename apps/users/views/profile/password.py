# ~*~ coding: utf-8 ~*~

from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic.edit import FormView

from authentication import errors
from authentication.mixins import AuthMixin
from common.utils import get_logger
from ... import forms
from ...utils import (
    get_user_or_pre_auth_user,
    LoginBlockUtil,
)

__all__ = ['UserVerifyPasswordView']

logger = get_logger(__name__)


class UserVerifyPasswordView(AuthMixin, FormView):
    template_name = 'users/user_password_verify.html'
    form_class = forms.UserCheckPasswordForm

    def form_valid(self, form):
        user = get_user_or_pre_auth_user(self.request)
        if user is None:
            return redirect('authentication:login')

        try:
            password = form.cleaned_data['password']
            ip = self.get_request_ip()
            self._set_partial_credential_error(user.username, ip, self.request)
            self._check_is_block(user.username)
            authenticated_user = self._check_auth_user_is_valid(user.username, password, '')
            if authenticated_user.pk != user.pk:
                self.raise_credential_error(errors.reason_password_failed)
        except errors.AuthFailedError as e:
            form.add_error("password", _("Password invalid") + f'({e.msg})')
            return self.form_invalid(form)

        LoginBlockUtil(user.username, ip).clean_failed_count()
        self.mark_password_ok(authenticated_user)
        return redirect(self.get_success_url())

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        else:
            return referer

    def get_context_data(self, **kwargs):
        context = {
            'user': get_user_or_pre_auth_user(self.request)
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
