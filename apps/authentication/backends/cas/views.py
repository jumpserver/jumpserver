from django_cas_ng.views import LoginView
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

__all__ = ['LoginView']


class CASLoginView(LoginView):
    def get(self, request):
        try:
            return super().get(request)
        except PermissionDenied:
            return HttpResponseRedirect('/')


