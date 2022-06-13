from django.utils.translation import ugettext as _
from tickets.models import ApplyLoginAssetTicket
from .base import BaseHandler


class Handler(BaseHandler):
    ticket: ApplyLoginAssetTicket
