from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from common.utils import lazyproperty
from .base import BaseAccount

__all__ = ['Account', 'AccountTemplate']


class Account(BaseAccount):
    class InnerAccount(models.TextChoices):
        INPUT = '@INPUT', '@INPUT'
        USER = '@USER', '@USER'

    asset = models.ForeignKey(
        'assets.Asset', related_name='accounts',
        on_delete=models.CASCADE, verbose_name=_('Asset')
    )
    su_from = models.ForeignKey(
        'assets.Account', related_name='su_to', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Su from")
    )
    version = models.IntegerField(default=0, verbose_name=_('Version'))
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Account')
        unique_together = [
            ('username', 'asset', 'secret_type'),
            ('name', 'asset'),
        ]
        permissions = [
            ('view_accountsecret', _('Can view asset account secret')),
            ('change_accountsecret', _('Can change asset account secret')),
            ('view_historyaccount', _('Can view asset history account')),
            ('view_historyaccountsecret', _('Can view asset history account secret')),
        ]

    @lazyproperty
    def platform(self):
        return self.asset.platform

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset.name)

    @classmethod
    def get_input_account(cls):
        """ @INPUT 手动登录的账号(any) """
        return cls(name=cls.InnerAccount.INPUT.value, username='')

    @classmethod
    def get_user_account(cls, username):
        """ @USER 动态用户的账号(self) """
        return cls(name=cls.InnerAccount.USER.value, username=username)

    @classmethod
    def filter(cls, asset_ids, account_usernames):
        queries = Q(asset_id__in=asset_ids) & Q(username__in=account_usernames)
        return cls.objects.filter(queries)


class AccountTemplate(BaseAccount):
    class Meta:
        verbose_name = _('Account template')
        unique_together = (
            ('name', 'org_id'),
        )

    def __str__(self):
        return self.username
