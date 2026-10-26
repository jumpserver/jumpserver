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
        from orgs.utils import tmp_to_root_org
        with tmp_to_root_org():
            for token in self.connection_tokens.order_by('pk'):
                token.complete_acl_requirement('review')

    class Meta:
        verbose_name = _('Apply Login Asset Ticket')
