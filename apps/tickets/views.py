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
        assigned_open_count = Ticket.get_assigned_tickets(self.request.user)\
            .filter(status=Ticket.STATUS_OPEN).count()
        context.update({
            'app': _("Tickets"),
            'action': _("Ticket list"),
            'assign': assign,
            'assigned_open_count': assigned_open_count
        })
        return context


class TicketDetailView(PermissionsMixin, mixins.TicketMixin, DetailView):
    template_name = 'tickets/ticket_detail.html'
    permission_classes = (IsValidUser,)
    queryset = Ticket.objects.all()

    def get_context_data(self, **kwargs):
        ticket = self.get_object()
        has_action_perm = ticket.is_assignee(self.request.user)
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _("Tickets"),
            'action': _("Ticket detail"),
            'has_action_perm': has_action_perm,
        })
        return context
