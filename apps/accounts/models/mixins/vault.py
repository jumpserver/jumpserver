from typing import Any
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from common.db import fields
from common.db.utils import Encryptor


__all__ = ['VaultQuerySetMixin', 'VaultManagerMixin', 'VaultModelMixin']


class VaultQuerySetMixin(models.QuerySet):

    def update(self, **kwargs):
        from accounts.const import VaultType
        exist_secret = 'secret' in kwargs
        is_local = settings.VAULT_TYPE == VaultType.LOCAL

        secret = kwargs.pop('secret', None)
        if exist_secret:
            kwargs['_secret'] = secret

        super().update(**kwargs)

        if is_local:
            return

        ids = self.values_list('id', flat=True)
        qs = self.model.objects.filter(id__in=ids)
        for obj in qs:
            if exist_secret:
                obj.secret = secret
            post_save.send(obj.__class__, instance=obj, created=False)


class VaultManagerMixin(models.Manager):

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        objs = super().bulk_create(objs, batch_size=batch_size, ignore_conflicts=ignore_conflicts)
        for obj in objs:
            post_save.send(obj.__class__, instance=obj, created=True)
        return objs

    def bulk_update(self, objs, batch_size=None, ignore_conflicts=False):
        objs = super().bulk_update(objs, batch_size=batch_size, ignore_conflicts=ignore_conflicts)
        for obj in objs:
            post_save.send(obj.__class__, instance=obj, created=False)
        return objs


class VaultModelMixin(models.Model):
    _secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Secret'))

    cache_secret: Any
    is_sync_secret = False

    class Meta:
        abstract = True

    @property
    def secret(self):
        from accounts.backends import vault_client
        secret = vault_client.get(self).get('secret')
        return secret

    @secret.setter
    def secret(self, value):
        if value is not None:
            value = Encryptor(value).encrypt()

        self.is_sync_secret = True
        self._secret = value

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 通过 post_save signal 处理 secret 数据


