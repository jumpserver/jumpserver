# -*- coding: utf-8 -*-
#

from django.db import models
from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from simple_history.models import HistoricalRecords

from common.utils import lazyproperty, get_logger
from .base import BaseUser, AbsConnectivity

logger = get_logger(__name__)


__all__ = ['AuthBook']


class AuthBook(BaseUser, AbsConnectivity):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    systemuser = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE, null=True, verbose_name=_("System user"))
    version = models.IntegerField(default=1, verbose_name=_('Version'))
    history = HistoricalRecords()

    auth_attrs = ['username', 'password', 'private_key', 'public_key']

    class Meta:
        verbose_name = _('AuthBook')
        unique_together = [('username', 'asset', 'systemuser')]
        permissions = [
            ('test_authbook', _('Can test asset account connectivity')),
            ('view_assetaccountsecret', _('Can view asset account secret')),
            ('change_assetaccountsecret', _('Can change asset account secret')),
            ('view_assethistoryaccount', _('Can view asset history account')),
            ('view_assethistoryaccountsecret', _('Can view asset history account secret')),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_snapshot = {}

    def get_or_systemuser_attr(self, attr):
        val = getattr(self, attr, None)
        if val:
            return val
        if self.systemuser:
            return getattr(self.systemuser, attr, '')
        return ''

    def load_auth(self):
        for attr in self.auth_attrs:
            value = self.get_or_systemuser_attr(attr)
            self.auth_snapshot[attr] = [getattr(self, attr), value]
            setattr(self, attr, value)

    def unload_auth(self):
        if not self.systemuser:
            return

        for attr, values in self.auth_snapshot.items():
            origin_value, loaded_value = values
            current_value = getattr(self, attr, '')
            if current_value == loaded_value:
                setattr(self, attr, origin_value)

    def save(self, *args, **kwargs):
        self.unload_auth()
        instance = super().save(*args, **kwargs)
        self.load_auth()
        return instance

    @property
    def username_display(self):
        return self.get_or_systemuser_attr('username') or '*'

    @lazyproperty
    def systemuser_display(self):
        if not self.systemuser:
            return ''
        return str(self.systemuser)

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

        # 不触发post_save信号
        self.__class__.objects.bulk_update(matched, fields=['password', 'private_key', 'public_key'])

    def remove_asset_admin_user_if_need(self):
        if not self.asset or not self.systemuser:
            return
        if not self.systemuser.is_admin_user or self.asset.admin_user != self.systemuser:
            return
        self.asset.admin_user = None
        self.asset.save()
        logger.debug('Remove asset admin user: {} {}'.format(self.asset, self.systemuser))

    def update_asset_admin_user_if_need(self):
        if not self.asset or not self.systemuser:
            return
        if not self.systemuser.is_admin_user or self.asset.admin_user == self.systemuser:
            return
        self.asset.admin_user = self.systemuser
        self.asset.save()
        logger.debug('Update asset admin user: {} {}'.format(self.asset, self.systemuser))

    @classmethod
    def get_queryset(cls):
        queryset = cls.objects.all() \
            .annotate(ip=F('asset__ip')) \
            .annotate(hostname=F('asset__hostname')) \
            .annotate(platform=F('asset__platform__name')) \
            .annotate(protocols=F('asset__protocols'))
        return queryset

    def __str__(self):
        return self.smart_name

