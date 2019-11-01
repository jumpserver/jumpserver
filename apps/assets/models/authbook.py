# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgManager
from .base import AssetUser

__all__ = ['AuthBook']


class AuthBookQuerySet(models.QuerySet):

    def latest_version(self):
        return self.filter(is_latest=True).filter(is_active=True)


class AuthBookManager(OrgManager):
    pass


class AuthBook(AssetUser):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest version'))
    version = models.IntegerField(default=1, verbose_name=_('Version'))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    objects = AuthBookManager.from_queryset(AuthBookQuerySet)()
    backend = "db"
    # 用于system user和admin_user的动态设置
    _connectivity = None
    CONN_CACHE_KEY = "ASSET_USER_CONN_{}"

    class Meta:
        verbose_name = _('AuthBook')

    def set_to_latest(self):
        self.remove_pre_latest()
        self.is_latest = True
        self.save()

    def get_pre_latest(self):
        pre_obj = self.__class__.objects.filter(
            username=self.username, asset=self.asset
        ).latest_version().first()
        return pre_obj

    def remove_pre_latest(self):
        pre_obj = self.get_pre_latest()
        if pre_obj:
            pre_obj.is_latest = False
            pre_obj.save()

    def set_version(self):
        pre_obj = self.get_pre_latest()
        if pre_obj:
            self.version = pre_obj.version + 1
        else:
            self.version = 1
        self.save()

    def get_related_assets(self):
        return [self.asset]

    def generate_id_with_asset(self, asset):
        return self.id

    @property
    def connectivity(self):
        return self.get_asset_connectivity(self.asset)

    @property
    def keyword(self):
        return '{}_#_{}'.format(self.username, str(self.asset.id))

    @property
    def hostname(self):
        return self.asset.hostname

    @property
    def ip(self):
        return self.asset.ip

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset)

