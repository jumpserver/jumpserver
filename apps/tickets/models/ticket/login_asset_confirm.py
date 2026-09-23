from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket

__all__ = ['ApplyLoginAssetTicket']

from ...const import TicketType


class ApplyLoginAssetTicket(Ticket):
    apply_login_user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, verbose_name=_('Login user'),
    )
    apply_login_asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL, null=True, verbose_name=_('Login asset'),
    )
    apply_login_account = models.CharField(
        max_length=128, default='', verbose_name=_('Login account')
    )

    TICKET_TYPE = TicketType.login_asset_confirm

    def activate_connection_token_if_need(self):
        token = getattr(self, 'connection_token', None)
        if not token:
            return
        if token.is_expired:
            from tickets.workflow.errors import WorkflowConfigurationError
            raise WorkflowConfigurationError('The connection token has expired. Request a new connection.')
        token.is_active = True
        token.save(update_fields=['is_active'])

    class Meta:
        verbose_name = _('Apply Login Asset Ticket')
