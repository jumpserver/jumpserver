# -*- coding: utf-8 -*-
#

from django.db import models, transaction
from django.db.models import Max
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgManager
from .base import BaseUser

__all__ = ['AuthBook']


class AuthBookQuerySet(models.QuerySet):
    def delete(self):
        if self.count() > 1:
            raise PermissionError(_("Bulk delete deny"))
        return super().delete()


class AuthBookManager(OrgManager):
    pass


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

    @classmethod
    def get_max_version(cls, username, asset):
        version_max = cls.objects.filter(username=username, asset=asset) \
            .aggregate(Max('version'))
        version_max = version_max['version__max'] or 0
        return version_max

    @classmethod
    def create(cls, **kwargs):
        """
        使用并发锁机制创建AuthBook对象, (主要针对并发创建 username, asset 相同的对象时)
        并更新其他对象的 is_latest=False (其他对象: 与当前对象的 username, asset 相同)
        同时设置自己的 is_latest=True, version=max_version + 1
        """
        username = kwargs['username']
        asset = kwargs['asset']
        key_lock = 'KEY_LOCK_CREATE_AUTH_BOOK_{}_{}'.format(username, asset.id)
        with cache.lock(key_lock):
            with transaction.atomic():
                cls.objects.filter(
                    username=username, asset=asset, is_latest=True
                ).update(is_latest=False)
                max_version = cls.get_max_version(username, asset)
                kwargs.update({
                    'version': max_version + 1,
                    'is_latest': True
                })
                obj = cls.objects.create(**kwargs)
                return obj

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

