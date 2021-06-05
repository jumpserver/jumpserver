# -*- coding: utf-8 -*-
#

from django.db import models
from django.db.models import Max
from django.utils.translation import ugettext_lazy as _

from simple_history.models import HistoricalRecords


from .base import BaseUser

__all__ = ['AuthBook']


class BaseAuthBook(BaseUser):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    system_user = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE, null=True, verbose_name=_("System user"))
    version = models.IntegerField(default=1, verbose_name=_('Version'))

    class Meta:
        abstract = True


class AuthBook(BaseAuthBook):
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest version'))
    history = HistoricalRecords()

    backend = "db"
    # 用于system user和admin_user的动态设置
    _connectivity = None
    CONN_CACHE_KEY = "ASSET_USER_CONN_{}"

    class Meta:
        verbose_name = _('AuthBook')
        unique_together = [('asset', 'system_user')]

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

    # def save(self):
    #     username = self.username
    #     asset = self.asset
    #
    #     with transaction.atomic():
    #         # 使用select_for_update限制并发创建相同的username、asset条目
    #         instances = AuthBook.objects.filter(username=username, asset=asset).select_for_update()
    #         versions = list(instances.values_list('version', flat=True))
    #         versions.append(1)
    #         max_version = max(versions)
    #         self.version = max_version + 1
    #         instances.delete()
    #         return super().save()

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

