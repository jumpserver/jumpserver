from tickets.models import ApplyCommandTicket
from .base import BaseHandler


class Handler(BaseHandler):
    ticket: ApplyCommandTicket
