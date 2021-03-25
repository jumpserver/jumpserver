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
        unique_together = ('name', 'safe')

    def __str__(self):
        return self.name
