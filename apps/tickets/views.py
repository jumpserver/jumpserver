from django.views.generic import TemplateView, DetailView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsOrgAdmin
from .models import LoginConfirmTicket


class LoginConfirmTicketListView(PermissionsMixin, TemplateView):
    template_name = 'tickets/login_confirm_ticket_list.html'
    permission_classes = (IsOrgAdmin,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Tickets"),
            'action': _("Login confirm ticket list")
        })
        return context


class LoginConfirmTicketDetailView(PermissionsMixin, DetailView):
    template_name = 'tickets/login_confirm_ticket_detail.html'
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        return LoginConfirmTicket.objects.filter(assignees=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Tickets"),
            'action': _("Login confirm ticket detail")
        })
        return context
