from django.views.generic import TemplateView, DetailView
from django.utils.translation import ugettext as _

from common.permissions import PermissionsMixin, IsValidUser
from .models import Ticket
from . import mixins


class TicketListView(PermissionsMixin, TemplateView):
    template_name = 'tickets/ticket_list.html'
    permission_classes = (IsValidUser,)

    def get_context_data(self, **kwargs):
        assign = self.request.GET.get('assign', '0') == '1'
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Tickets"),
            'action': _("Ticket list"),
            'assign': assign,
        })
        return context


class TicketDetailView(PermissionsMixin, mixins.TicketMixin, DetailView):
    template_name = 'tickets/ticket_detail.html'
    permission_classes = (IsValidUser,)
    queryset = Ticket.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Tickets"),
            'action': _("Ticket detail")
        })
        return context
