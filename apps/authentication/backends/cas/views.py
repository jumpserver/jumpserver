from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.views.generic import View
from django_cas_ng.views import LoginView

__all__ = ['LoginView']

from authentication.views.utils import redirect_to_guard_view


class CASLoginView(LoginView):
    def get(self, request):
        try:
            return super().get(request)
        except PermissionDenied:
            return HttpResponseRedirect('/')


class CASCallbackClientView(View):
    http_method_names = ['get', ]

    def get(self, request):
        return redirect_to_guard_view(query_string='next=client')
