# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from orgs.mixins import OrgManager

from .base import AssetUser
from ..const import ASSET_USER_CONN_CACHE_KEY

__all__ = ['AuthBook']


class AuthBookQuerySet(models.QuerySet):

    def latest_version(self):
        return self.filter(is_latest=True)


class AuthBookManager(OrgManager):
    pass


class AuthBook(AssetUser):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest version'))
    version = models.IntegerField(default=1, verbose_name=_('Version'))

    objects = AuthBookManager.from_queryset(AuthBookQuerySet)()

    class Meta:
        verbose_name = _('AuthBook')

    def _set_latest(self):
        self._remove_pre_obj_latest()
        self.is_latest = True
        self.save()

    def _get_pre_obj(self):
        pre_obj = self.__class__.objects.filter(
            username=self.username, asset=self.asset).latest_version().first()
        return pre_obj

    def _remove_pre_obj_latest(self):
        pre_obj = self._get_pre_obj()
        if pre_obj:
            pre_obj.is_latest = False
            pre_obj.save()

    def _set_version(self):
        pre_obj = self._get_pre_obj()
        if pre_obj:
            self.version = pre_obj.version + 1
        else:
            self.version = 1
        self.save()

    def set_version_and_latest(self):
        self._set_version()
        self._set_latest()

    @property
    def _conn_cache_key(self):
        return ASSET_USER_CONN_CACHE_KEY.format(self.id, self.asset.id)

    @property
    def connectivity(self):
        value = cache.get(self._conn_cache_key, self.UNKNOWN)
        return value

    @connectivity.setter
    def connectivity(self, value):
        _connectivity = self.UNKNOWN

        for host in value.get('dark', {}).keys():
            if host == self.asset.hostname:
                _connectivity = self.UNREACHABLE

        for host in value.get('contacted', []):
            if host == self.asset.hostname:
                _connectivity = self.REACHABLE

        cache.set(self._conn_cache_key, _connectivity, 3600)

    @property
    def keyword(self):
        return {'username': self.username, 'asset': self.asset}

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset)

