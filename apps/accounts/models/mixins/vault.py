from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

from common.db import fields


__all__ = ['VaultQuerySetMixin', 'VaultManagerMixin', 'VaultModelMixin']


class VaultQuerySetMixin(models.QuerySet):

    def update(self, **kwargs):
        """
           1. 替换 secret 为 _secret
           2. 触发 post_save 信号
        """
        secret = kwargs.pop('secret', None)
        if secret:
            # 替换 _secret 值
            kwargs.update({
                '_secret': secret
            })
        rows = super().update(**kwargs)

        # 为了获取更新后的对象所以单独查询一次
        ids = self.values_list('id', flat=True)
        objs = self.model.objects.filter(id__in=ids)
        for obj in objs:
            post_save.send(obj.__class__, instance=obj, created=False)
        return rows


class VaultManagerMixin(models.Manager):
    """ 触发 bulk_create 和 bulk_update 操作下的 post_save 信号 """

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

    class Meta:
        abstract = True

    @property
    def secret(self):
        """ 先通过 vault_client 获取，如果获取不到再从 self._secret 获取 """
        from accounts.backends import vault_client
        secret = vault_client.get(self).get('secret')
        if not secret:
            secret = self._secret
        return secret

    @secret.setter
    def secret(self, value):
        """
        保存的时候通过 post_save 信号监听进行处理,
        先保存到 db, 再保存到 vault 同时删除本地 db _secret 值
        """
        self._secret = value

    secret_save_to_vault_mark = '# Secret-has-been-saved-to-vault #'

    def mark_secret_save_to_vault(self):
        self._secret = self.secret_save_to_vault_mark
        self.save()

    @property
    def secret_need_save_to_vault(self):
        return self._secret == self.secret_save_to_vault_mark

    def save(self, *args, **kwargs):
        """ 通过 post_save signal 处理 _secret 数据 """
        return super().save(*args, **kwargs)


