from tickets.models import ApplyLoginAssetTicket
from .base import BaseHandler


class Handler(BaseHandler):
    ticket: ApplyLoginAssetTicket

    def _on_step_approved(self, step):
        is_finished = super()._on_step_approved(step)
        if is_finished:
            self.ticket.connection_token.is_active = True
            self.ticket.connection_token.save()
        return is_finished
