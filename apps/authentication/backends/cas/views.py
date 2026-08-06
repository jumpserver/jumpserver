from django.contrib.auth import logout as auth_logout
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_cas_ng.views import LoginView

from authentication.views.mixins import FlashMessageMixin

__all__ = ['LoginView']


class CASLoginView(LoginView, FlashMessageMixin):
    def get(self, request):
        try:
            resp = super().get(request)
        except PermissionDenied:
            resp = HttpResponseRedirect('/')
        error_message = getattr(request, 'error_message', '')
        if error_message:
            auth_logout(request)
            redirect_url = reverse('authentication:login') + '?admin=1'
            response = self.get_failed_response(
                redirect_url, title=_('CAS Error'), msg=error_message
            )
            return response
        else:
            return resp
