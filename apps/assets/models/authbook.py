# -*- coding: utf-8 -*-
#

from django.db import models
from django.db.models import Max
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgManager
from .base import BaseUser

__all__ = ['AuthBook']


class AuthBookQuerySet(models.QuerySet):
    def delete(self):
        raise PermissionError("Bulk delete authbook deny")


class AuthBookManager(OrgManager):

    def get_max_version(self, username, asset):
        version_max = self.filter(username=username, asset=asset)\
            .aggregate(Max('version'))
        version_max = version_max['version__max'] or 0
        return version_max

    def create(self, **kwargs):
        username = kwargs['username']
        asset = kwargs['asset']
        key_lock = 'KEY_LOCK_CREATE_AUTH_BOOK_{}_{}'.format(username, asset.id)
        with cache.lock(key_lock, expire=60):
            self.filter(username=username, asset=asset, is_latest=True)\
                .update(is_latest=False)
            max_version = self.get_max_version(username, asset)
            kwargs['version'] = max_version + 1
            kwargs['is_latest'] = True
            obj = super().create(**kwargs)
        return obj


class AuthBook(BaseUser):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest version'))
    version = models.IntegerField(default=1, verbose_name=_('Version'))

    objects = AuthBookManager.from_queryset(AuthBookQuerySet)()
    backend = "db"
    # 用于system user和admin_user的动态设置
    _connectivity = None
    CONN_CACHE_KEY = "ASSET_USER_CONN_{}"

    class Meta:
        verbose_name = _('AuthBook')

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

