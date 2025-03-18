from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket

__all__ = ['ApplyLoginTicket']

from ...const import TicketType


class ApplyLoginTicket(Ticket):
    apply_login_ip = models.GenericIPAddressField(verbose_name=_('Login IP'), null=True)
    apply_login_city = models.CharField(max_length=64, verbose_name=_('Login city'), null=True)
    apply_login_datetime = models.DateTimeField(verbose_name=_('Login Date'), null=True)

    TICKET_TYPE = TicketType.login_confirm

    class Meta:
        verbose_name = _('Apply Login Ticket')
