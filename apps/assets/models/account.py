from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from common.utils import lazyproperty
from .base import BaseAccount, AbsConnectivity

__all__ = ['Account', 'AccountTemplate']


class AccountHistoricalRecords(HistoricalRecords):
    def __init__(self, *args, **kwargs):
        self.included_fields = kwargs.pop('included_fields', None)
        super().__init__(*args, **kwargs)

    def post_save(self, instance, created, using=None, **kwargs):
        if not self.included_fields:
            return super().post_save(instance, created, using=using, **kwargs)

        check_fields = set(self.included_fields) - {'version'}
        history_attrs = instance.history.all().values(*check_fields).first()
        if history_attrs is None:
            return super().post_save(instance, created, using=using, **kwargs)

        attrs = {field: getattr(instance, field) for field in check_fields}
        history_attrs = set(history_attrs.items())
        attrs = set(attrs.items())
        diff = attrs - history_attrs
        if not diff:
            return
        super().post_save(instance, created, using=using, **kwargs)

    def fields_included(self, model):
        if self.included_fields:
            fields = [i for i in model._meta.fields if i.name in self.included_fields]
            return fields
        return super().fields_included(model)


class Account(AbsConnectivity, BaseAccount):
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
    history = AccountHistoricalRecords(included_fields=['id', 'secret', 'secret_type', 'version'])

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
        return '{}'.format(self.username)

    @classmethod
    def get_input_account(cls):
        """ @INPUT 手动登录的账号(any) """
        return cls(name=cls.InnerAccount.INPUT.value, username='')

    @classmethod
    def get_user_account(cls, username):
        """ @USER 动态用户的账号(self) """
        return cls(name=cls.InnerAccount.USER.value, username=username)


class AccountTemplate(BaseAccount):
    class Meta:
        verbose_name = _('Account template')
        unique_together = (
            ('name', 'org_id'),
        )

    def __str__(self):
        return self.username
