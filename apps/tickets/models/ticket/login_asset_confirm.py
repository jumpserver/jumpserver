from django.db import models
from django.utils.translation import gettext_lazy as _

from .general import Ticket

__all__ = ['ApplyLoginAssetTicket']


class ApplyLoginAssetTicket(Ticket):
    apply_login_user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True,
        verbose_name=_('Login user'),
    )
    apply_login_asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL, null=True,
        verbose_name=_('Login asset'),
    )
    apply_login_account = models.CharField(
        max_length=128, default='', verbose_name=_('Login account')
    )
