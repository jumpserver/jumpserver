# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _

from simple_history.models import HistoricalRecords


from .base import BaseUser, AbsConnectivity

__all__ = ['AuthBook']


class AuthBook(BaseUser, AbsConnectivity):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    systemuser = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE, null=True, verbose_name=_("System user"))
    version = models.IntegerField(default=1, verbose_name=_('Version'))
    # Todo: 移除
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest version'))
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('AuthBook')
        unique_together = [('username', 'asset', 'systemuser')]

    @property
    def username_display(self):
        if self.username:
            return self.username
        if self.systemuser:
            return self.systemuser.username
        return ''

    @property
    def smart_name(self):
        username = self.username_display

        if self.asset:
            asset = str(self.asset)
        else:
            asset = '*'
        return '{}@{}'.format(username, asset)

    def __str__(self):
        return self.smart_name

