from tickets.models import ApplyLoginAssetTicket
from .base import BaseHandler


class Handler(BaseHandler):
    ticket: ApplyLoginAssetTicket

    def _on_step_approved(self, step):
        is_finished = super()._on_step_approved(step)
        if is_finished:
            self.ticket.activate_connection_token_if_need()
        return is_finished
