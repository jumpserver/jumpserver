from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from common.utils import lazyproperty
from ..const import AliasAccount, Source
from assets.models.base import AbsConnectivity
from .base import BaseAccount

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

    def create_history_model(self, model, inherited):
        if self.included_fields and not self.excluded_fields:
            self.excluded_fields = [
                field.name for field in model._meta.fields
                if field.name not in self.included_fields
            ]
        return super().create_history_model(model, inherited)


class Account(AbsConnectivity, BaseAccount):
    asset = models.ForeignKey(
        'assets.Asset', related_name='accounts',
        on_delete=models.CASCADE, verbose_name=_('Asset')
    )
    su_from = models.ForeignKey(
        'accounts.Account', related_name='su_to', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Su from")
    )
    version = models.IntegerField(default=0, verbose_name=_('Version'))
    history = AccountHistoricalRecords(included_fields=['id', 'secret', 'secret_type', 'version'])
    source = models.CharField(max_length=30, default=Source.LOCAL, verbose_name=_('Source'))

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

    @lazyproperty
    def alias(self):
        if self.username.startswith('@'):
            return self.username
        return self.name

    def __str__(self):
        return '{}'.format(self.username)

    @lazyproperty
    def has_secret(self):
        return bool(self.secret)

    @classmethod
    def get_manual_account(cls):
        """ @INPUT 手动登录的账号(any) """
        return cls(name=AliasAccount.INPUT.label, username=AliasAccount.INPUT.value, secret=None)

    @classmethod
    def get_user_account(cls, username):
        """ @USER 动态用户的账号(self) """
        return cls(name=AliasAccount.USER.label, username=AliasAccount.USER.value)

    def get_su_from_accounts(self):
        """ 排除自己和以自己为 su-from 的账号 """
        return self.asset.accounts.exclude(id=self.id).exclude(su_from=self)


class AccountTemplate(BaseAccount):
    class Meta:
        verbose_name = _('Account template')
        unique_together = (
            ('name', 'org_id'),
        )
        permissions = [
            ('view_accounttemplatesecret', _('Can view asset account template secret')),
            ('change_accounttemplatesecret', _('Can change asset account template secret')),
        ]

    def __str__(self):
        return self.username
