from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket

__all__ = ['ApplyLoginAssetTicket']


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

    def activate_connection_token_if_need(self):
        if not self.connection_token:
            return
        self.connection_token.is_active = True
        self.connection_token.save()

    class Meta:
        verbose_name = _('Apply Login Asset Ticket')
