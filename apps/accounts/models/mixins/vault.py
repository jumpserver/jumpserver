from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _

from common.db import fields

__all__ = ['VaultQuerySetMixin', 'VaultManagerMixin', 'VaultModelMixin']


class VaultQuerySetMixin(models.QuerySet):

    def update(self, **kwargs):
        """
           1. 替换 secret 为 _secret
           2. 触发 post_save 信号
        """
        if 'secret' in kwargs:
            kwargs.update({
                '_secret': kwargs.pop('secret')
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

    def bulk_update(self, objs, fields, batch_size=None):
        fields = ["_secret" if field == "secret" else field for field in fields]
        super().bulk_update(objs, fields, batch_size=batch_size)
        for obj in objs:
            post_save.send(obj.__class__, instance=obj, created=False)
        return objs


class VaultModelMixin(models.Model):
    _secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Secret'))
    is_sync_metadata = True

    class Meta:
        abstract = True

    # 缓存 secret 值, lazy-property 不能用
    __secret = None

    @property
    def secret(self):
        if self.__secret:
            return self.__secret
        from accounts.backends import vault_client
        secret = vault_client.get(self)
        if not secret and not self.secret_has_save_to_vault:
            # vault_client 获取不到, 并且 secret 没有保存到 vault, 就从 self._secret 获取
            secret = self._secret
        self.__secret = secret
        return self.__secret

    @secret.setter
    def secret(self, value):
        """
        保存的时候通过 post_save 信号监听进行处理,
        先保存到 db, 再保存到 vault 同时删除本地 db _secret 值
        """
        self._secret = value
        self.__secret = value

    _secret_save_to_vault_mark = '# Secret-has-been-saved-to-vault #'

    def mark_secret_save_to_vault(self):
        self._secret = self._secret_save_to_vault_mark
        self.save()

    @property
    def secret_has_save_to_vault(self):
        return self._secret == self._secret_save_to_vault_mark

    def save(self, *args, **kwargs):
        """ 通过 post_save signal 处理 _secret 数据 """
        update_fields = kwargs.get('update_fields')
        if update_fields and 'secret' in update_fields:
            update_fields.remove('secret')
            update_fields.append('_secret')
        return super().save(*args, **kwargs)
