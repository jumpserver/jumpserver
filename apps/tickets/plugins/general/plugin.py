from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'general'
    label = _('General')
    visible = False
