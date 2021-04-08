import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin
from orgs.mixins.models import OrgModelMixin


__all__ = ['Account']


class Account(CommonModelMixin, OrgModelMixin):
    """ 账号: 可以直接使用的最小单元 """
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    username = models.CharField(max_length=2048, verbose_name=_('Username'))
    secret = models.TextField(max_length=4096, verbose_name=_('Secret'))
    address = models.CharField(max_length=4096, verbose_name=_('Address'))
    # type -> fields
    type = models.ForeignKey('AccountType', on_delete=models.PROTECT, verbose_name=_('Type'))
    attrs = models.JSONField(default=dict, verbose_name=_('Attributes'))
    is_privileged = models.BooleanField(default=False, verbose_name=_('Privileged'))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    safe = models.ForeignKey('accounts.Safe', on_delete=models.PROTECT, verbose_name=_('Safe'))

    class Meta:
        permissions = [
            # ('codename', 'name')
            ("view_account_secret", "Can view the secret of account"),
        ]
        unique_together = ('name', 'safe')

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        # 提前保存ID值
        _id = uuid.UUID(str(self.id))
        super().delete(using=using, keep_parents=keep_parents)

        self.id = _id
        self._delete_secret()

    def _delete_secret(self):
        from ..backends import storage
        storage.delete_secret(account=self)

    def _undelete_secret(self, account_id):
        from ..backends import storage
        storage.undelete_secret(account=self)

    def save(self, *args, **kwargs):
        secret, self.secret = self.secret, ''
        super().save(*args, **kwargs)
        self._save_secret(secret)

    def _save_secret(self, secret):
        if not secret:
            return
        from ..backends import storage
        secret_data = self._package_secret(secret)
        storage.update_or_create(account=self, secret_data=secret_data)

    def read_secret(self, version=None):
        from ..backends import storage
        secret_data = storage.read_secret(account=self, version=version)
        secret = self._unpack_secret_data(secret_data)
        return secret

    def get_secret_versions(self):
        from ..backends import storage
        versions = storage.get_secret_versions(account=self)
        return versions

    storage_key_of_secret_field = 'secret'

    def _package_secret(self, secret):
        """ 打包 secret """
        secret_data = {
            self.storage_key_of_secret_field: secret
        }
        return secret_data

    def _unpack_secret_data(self, secret_data: dict):
        """ 解包 secret_data """
        secret = secret_data.get(self.storage_key_of_secret_field)
        return secret


