from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import redirect
from common.permissions import PermissionsMixin, IsValidUser

__all__ = ['IndexView']


class IndexView(PermissionsMixin, TemplateView):
    template_name = 'index.html'
    permission_classes = [IsValidUser]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_common_user:
            return redirect('assets:user-asset-list')
        return super(IndexView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Dashboard"),
        })
        return context
