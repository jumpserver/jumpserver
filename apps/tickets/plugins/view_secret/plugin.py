from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'view_secret'
    label = _('View account password')
    self_service = True
    request_serializer = 'tickets.plugins.view_secret.serializer.RequestSerializer'

    def build_context(self, ticket):
        from ..resources import account_context
        context = account_context(ticket)
        context.update(actions=['view_secret'], duration=ticket.request_data['duration'])
        return context
