from django.db import models
from django.utils.translation import gettext_lazy as _

from .base import UserBaseACL

__all__ = ['ConnectMethodACL']


class ConnectMethodACL(UserBaseACL):
    connect_methods = models.JSONField(default=list, verbose_name=_('Connect methods'))

    class Meta(UserBaseACL.Meta):
        verbose_name = _('Connect method acl')
        abstract = False
