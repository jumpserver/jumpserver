from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'change_secret'
    label = _('Change account password')
    self_service = True
    request_serializer = 'tickets.plugins.resources.AssetAccountRequestSerializer'

    def build_context(self, ticket):
        from ..resources import account_context
        return {**account_context(ticket), 'actions': ['change_secret']}
