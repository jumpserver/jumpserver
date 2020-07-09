from django.views.generic import TemplateView
from django.shortcuts import redirect
from common.permissions import PermissionsMixin, IsValidUser

__all__ = ['IndexView']


class IndexView(PermissionsMixin, TemplateView):
    template_name = 'index.html'
    permission_classes = [IsValidUser]

    def get(self, request, *args, **kwargs):
        return redirect('/ui/')
