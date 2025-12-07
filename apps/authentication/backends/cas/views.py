from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
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
            response = self.get_failed_response('/', title=_('CAS Error'), msg=error_message)
            return response
        else:
            return resp
