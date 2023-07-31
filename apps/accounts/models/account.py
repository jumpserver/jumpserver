from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from assets.models.base import AbsConnectivity
from common.utils import lazyproperty
from .base import BaseAccount
from .mixins import VaultModelMixin
from ..const import AliasAccount, Source

__all__ = ['Account', 'AccountTemplate', 'AccountHistoricalRecords']


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
        return super().post_save(instance, created, using=using, **kwargs)

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
    history = AccountHistoricalRecords(included_fields=['id', '_secret', 'secret_type', 'version'])
    source = models.CharField(max_length=30, default=Source.LOCAL, verbose_name=_('Source'))
    source_id = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Source ID'))

    class Meta:
        verbose_name = _('Account')
        unique_together = [
            ('username', 'asset', 'secret_type'),
            ('name', 'asset'),
        ]
        permissions = [
            ('view_accountsecret', _('Can view asset account secret')),
            ('view_historyaccount', _('Can view asset history account')),
            ('view_historyaccountsecret', _('Can view asset history account secret')),
            ('verify_account', _('Can verify account')),
            ('push_account', _('Can push account')),
        ]

    def __str__(self):
        return '{}'.format(self.username)

    @lazyproperty
    def platform(self):
        return self.asset.platform

    @lazyproperty
    def alias(self):
        if self.username.startswith('@'):
            return self.username
        return self.name

    @lazyproperty
    def has_secret(self):
        return bool(self.secret)

    @classmethod
    def get_special_account(cls, name):
        if name == AliasAccount.INPUT.value:
            return cls.get_manual_account()
        elif name == AliasAccount.ANON.value:
            return cls.get_anonymous_account()
        else:
            return cls(name=name, username=name, secret=None)

    @classmethod
    def get_manual_account(cls):
        """ @INPUT 手动登录的账号(any) """
        return cls(name=AliasAccount.INPUT.label, username=AliasAccount.INPUT.value, secret=None)

    @classmethod
    def get_anonymous_account(cls):
        return cls(name=AliasAccount.ANON.label, username=AliasAccount.ANON.value, secret=None)

    @classmethod
    def get_user_account(cls):
        """ @USER 动态用户的账号(self) """
        return cls(name=AliasAccount.USER.label, username=AliasAccount.USER.value, secret=None)

    @lazyproperty
    def versions(self):
        return self.history.count()

    def get_su_from_accounts(self):
        """ 排除自己和以自己为 su-from 的账号 """
        return self.asset.accounts.exclude(id=self.id).exclude(su_from=self)


class AccountTemplate(BaseAccount):
    su_from = models.ForeignKey(
        'self', related_name='su_to', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Su from")
    )

    class Meta:
        verbose_name = _('Account template')
        unique_together = (
            ('name', 'org_id'),
        )
        permissions = [
            ('view_accounttemplatesecret', _('Can view asset account template secret')),
            ('change_accounttemplatesecret', _('Can change asset account template secret')),
        ]

    @classmethod
    def get_su_from_account_templates(cls, pk=None):
        if pk is None:
            return cls.objects.all()
        return cls.objects.exclude(Q(id=pk) | Q(su_from_id=pk))

    def __str__(self):
        return f'{self.name}({self.username})'

    def get_su_from_account(self, asset):
        su_from = self.su_from
        if su_from and asset.platform.su_enabled:
            account = asset.accounts.filter(
                username=su_from.username,
                secret_type=su_from.secret_type
            ).first()
            return account

    def __str__(self):
        return self.username

    @staticmethod
    def bulk_update_accounts(accounts, data):
        history_model = Account.history.model
        account_ids = accounts.values_list('id', flat=True)
        history_accounts = history_model.objects.filter(id__in=account_ids)
        account_id_count_map = {
            str(i['id']): i['count']
            for i in history_accounts.values('id').order_by('id')
            .annotate(count=Count(1)).values('id', 'count')
        }

        for account in accounts:
            account_id = str(account.id)
            account.version = account_id_count_map.get(account_id) + 1
            for k, v in data.items():
                setattr(account, k, v)
        Account.objects.bulk_update(accounts, ['version', 'secret'])

    @staticmethod
    def bulk_create_history_accounts(accounts, user_id):
        history_model = Account.history.model
        history_account_objs = []
        for account in accounts:
            history_account_objs.append(
                history_model(
                    id=account.id,
                    version=account.version,
                    secret=account.secret,
                    secret_type=account.secret_type,
                    history_user_id=user_id,
                    history_date=timezone.now()
                )
            )
        history_model.objects.bulk_create(history_account_objs)

    def bulk_sync_account_secret(self, accounts, user_id):
        """ 批量同步账号密码 """
        if not accounts:
            return
        self.bulk_update_accounts(accounts, {'secret': self.secret})
        self.bulk_create_history_accounts(accounts, user_id)


def replace_history_model_with_mixin():
    """
    替换历史模型中的父类为指定的Mixin类。

    Parameters:
        model (class): 历史模型类，例如 Account.history.model
        mixin_class (class): 要替换为的Mixin类

    Returns:
        None
    """
    model = Account.history.model
    model.__bases__ = (VaultModelMixin,) + model.__bases__


replace_history_model_with_mixin()
