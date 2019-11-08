from django.views.generic import TemplateView, DetailView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsValidUser
from .models import LoginConfirmTicket
from . import mixins


class LoginConfirmTicketListView(PermissionsMixin, TemplateView):
    template_name = 'tickets/login_confirm_ticket_list.html'
    permission_classes = (IsValidUser,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Tickets"),
            'action': _("Login confirm ticket list")
        })
        return context


class LoginConfirmTicketDetailView(PermissionsMixin, mixins.TicketMixin, DetailView):
    template_name = 'tickets/login_confirm_ticket_detail.html'
    queryset = LoginConfirmTicket.objects.all()
    permission_classes = (IsValidUser,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Tickets"),
            'action': _("Login confirm ticket detail")
        })
        return context
