from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'file_transfer'
    label = _('File upload / download')
    self_service = True
    request_serializer = 'tickets.plugins.file_transfer.serializer.RequestSerializer'

    def build_context(self, ticket):
        from ..resources import account_context
        context = account_context(ticket)
        context.update(actions=[ticket.request_data['direction']], duration=ticket.request_data['duration'])
        return context
