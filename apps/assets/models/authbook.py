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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smarty_it()

    def get_or_systemuser_attr(self, attr):
        val = getattr(self, attr, None)
        if val:
            return val
        if self.systemuser:
            return getattr(self.systemuser, attr, '')
        return ''

    def smarty_it(self, *attrs):
        if not attrs:
            attrs = ['username', 'password', 'private_key', 'public_key']
        for attr in attrs:
            value = self.get_or_systemuser_attr(attr)
            setattr(self, attr, value)

    @property
    def username_display(self):
        return self.get_or_systemuser_attr('username') or '*'

    @property
    def smart_name(self):
        username = self.username_display

        if self.asset:
            asset = str(self.asset)
        else:
            asset = '*'
        return '{}@{}'.format(username, asset)

    def sync_to_system_user_account(self):
        if self.systemuser:
            return
        matched = AuthBook.objects.filter(
            asset=self.asset, systemuser__username=self.username
        )
        if not matched:
            return

        for i in matched:
            i.password = self.password
            i.private_key = self.private_key
            i.public_key = self.public_key
            i.comment = 'Update triggered by account {}'.format(self.id)
            i.save(update_fields=['password', 'private_key', 'public_key'])

    def __str__(self):
        return self.smart_name

