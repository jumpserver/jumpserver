from django.views.generic import TemplateView, DetailView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsOrgAdmin
from .models import LoginConfirmOrder


class LoginConfirmOrderListView(PermissionsMixin, TemplateView):
    template_name = 'orders/login_confirm_order_list.html'
    permission_classes = (IsOrgAdmin,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Orders"),
            'action': _("Login confirm order list")
        })
        return context


class LoginConfirmOrderDetailView(PermissionsMixin, DetailView):
    template_name = 'orders/login_confirm_order_detail.html'
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        return LoginConfirmOrder.objects.filter(assignees=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Orders"),
            'action': _("Login confirm order detail")
        })
        return context
