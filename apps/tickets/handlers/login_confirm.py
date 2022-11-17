from tickets.models import ApplyLoginTicket
from .base import BaseHandler


class Handler(BaseHandler):
    ticket: ApplyLoginTicket
