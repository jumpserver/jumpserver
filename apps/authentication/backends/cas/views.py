from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_cas_ng.views import LoginView

from authentication.views.mixins import FlashMessageMixin

__all__ = ['LoginView']


class CASLoginView(LoginView, FlashMessageMixin):
    def get(self, request):
        try:
            response = super().get(request)
        except PermissionDenied as exc:
            error_message = (
                getattr(request, 'error_message', '') or str(exc)
            )
        else:
            error_message = getattr(request, 'error_message', '')
            if not error_message:
                return response

        redirect_url = reverse('authentication:login') + '?admin=1'
        return self.get_failed_response(
            redirect_url, title=_('CAS Error'), msg=error_message
        )
