# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import PermissionDenied

from simple_history.models import HistoricalRecords


from .base import BaseUser

__all__ = ['AuthBook']


class AuthBook(BaseUser):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    systemuser = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE, null=True, verbose_name=_("System user"))
    # Todo: 移除
    version = models.IntegerField(default=1, verbose_name=_('Version'))
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest version'))
    history = HistoricalRecords()

    # 用于system user和admin_user的动态设置
    _connectivity = None
    CONN_CACHE_KEY = "ASSET_USER_CONN_{}"

    class Meta:
        verbose_name = _('AuthBook')
        unique_together = [('username', 'asset', 'systemuser')]

    @property
    def connectivity(self):
        return self.get_asset_connectivity(self.asset)

    def smart_name(self):
        if self.username:
            username = self.username
        elif self.systemuser:
            username = self.systemuser.username
        else:
            username = '*'

        if self.asset:
            asset = str(self.asset)
        else:
            asset = '*'
        return '{}@{}'.format(username, asset)

    def __str__(self):
        return self.smart_name()

