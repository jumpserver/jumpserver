from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes, Source
from accounts.models import Account
from common.const import ConfirmOrIgnore
from common.utils.timezone import is_date_more_than
from orgs.mixins.models import JMSOrgBaseModel
from .base import AccountBaseAutomation

__all__ = ['GatherAccountsAutomation', 'GatheredAccount', 'GatheredAccountDiff']


class GatheredAccountDiff(models.Model):
    account = models.ForeignKey('GatheredAccount', on_delete=models.CASCADE, verbose_name=_("Gathered account"))
    diff = models.TextField(default='', verbose_name=_("Diff"))
    item = models.CharField(max_length=32, default='', verbose_name=_("Item"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))


class GatheredAccount(JMSOrgBaseModel):
    present = models.BooleanField(default=True, verbose_name=_("Remote present"))  # 资产上是否还存在
    date_last_login = models.DateTimeField(null=True, verbose_name=_("Date login"))
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_("Asset"))
    username = models.CharField(max_length=32, blank=True, db_index=True, verbose_name=_('Username'))
    address_last_login = models.CharField(max_length=39, default='', verbose_name=_("Address login"))
    status = models.CharField(max_length=32, default='', blank=True, choices=ConfirmOrIgnore.choices, verbose_name=_("Status"))
    authorized_keys = models.TextField(default='', blank=True, verbose_name=_("Authorized keys"))
    sudoers = models.TextField(default='', verbose_name=_("Sudoers"), blank=True)
    groups = models.TextField(default='', blank=True, verbose_name=_("Groups"))

    @property
    def address(self):
        return self.asset.address

    @classmethod
    def find_account_risk(cls, gathered_account, accounts):
        pass

    @classmethod
    def update_exists_accounts(cls, gathered_account, accounts):
        if not gathered_account.date_last_login:
            return

        for account in accounts:
            # 这里是否可以考虑，标记成未从堡垒机登录风险 ？
            if is_date_more_than(gathered_account.date_last_login, account.date_last_login, '5m'):
                account.date_last_login = gathered_account.date_last_login
                account.login_by = '{}({})'.format('unknown', gathered_account.address_last_login)
                account.save(update_fields=['date_last_login', 'login_by'])

    @classmethod
    def create_accounts(cls, gathered_account):
        account_objs = []
        asset_id = gathered_account.asset_id
        username = gathered_account.username
        account = Account(
            asset_id=asset_id, username=username,
            name=username, source=Source.COLLECTED,
            date_last_login=gathered_account.date_last_login,
        )
        account_objs.append(account)
        Account.objects.bulk_create(account_objs)
        gathered_account.status = ConfirmOrIgnore.confirmed
        gathered_account.save(update_fields=['status'])

    @classmethod
    def sync_accounts(cls, gathered_accounts, auto_create=True):
        """
        更新为已存在的账号，或者创建新的账号, 原来的 sync 重构了，如果存在则自动更新一些信息
        """
        for gathered_account in gathered_accounts:
            asset_id = gathered_account.asset_id
            username = gathered_account.username
            accounts = Account.objects.filter(
                Q(asset_id=asset_id, username=username) |
                Q(asset_id=asset_id, name=username)
            )

            if accounts.exists():
                cls.update_exists_accounts(gathered_account, accounts)
            elif auto_create:
                cls.create_accounts(gathered_account)

    class Meta:
        verbose_name = _("Gather asset accounts")
        unique_together = [
            ('username', 'asset'),
        ]
        ordering = ['asset']

    def __str__(self):
        return '{}: {}'.format(self.asset, self.username)


class GatherAccountsAutomation(AccountBaseAutomation):
    is_sync_account = models.BooleanField(
        default=False, blank=True, verbose_name=_("Is sync account")
    )
    recipients = models.ManyToManyField('users.User', verbose_name=_("Recipient"), blank=True)

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'is_sync_account': self.is_sync_account,
            'recipients': [
                str(recipient.id) for recipient in self.recipients.all()
            ]
        })
        return attr_json

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.gather_accounts
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Gather account automation')
