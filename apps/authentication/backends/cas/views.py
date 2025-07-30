from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django_cas_ng.views import LoginView

from authentication.backends.base import BaseAuthCallbackClientView
from common.utils import FlashMessageUtil
from .backends import CASUserDoesNotExist

__all__ = ['LoginView']


class CASLoginView(LoginView):
    def get(self, request):
        try:
            resp = super().get(request)
            return resp
        except PermissionDenied:
            return HttpResponseRedirect('/')
        except CASUserDoesNotExist as e:
            message_data = {
                'title': _('User does not exist: {}').format(e),
                'error': _(
                    'CAS login was successful, but no corresponding local user was found in the system, and automatic '
                    'user creation is disabled in the CAS authentication configuration. Login failed.'),
                'interval': 10,
                'redirect_url': '/',
            }
            return FlashMessageUtil.gen_and_redirect_to(message_data)


class CASCallbackClientView(BaseAuthCallbackClientView):
    pass
