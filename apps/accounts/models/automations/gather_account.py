from collections import defaultdict

from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes, Source
from accounts.models import Account
from common.const import ConfirmOrIgnore
from common.utils.timezone import is_date_more_than
from orgs.mixins.models import JMSOrgBaseModel
from .base import AccountBaseAutomation

__all__ = ['GatherAccountsAutomation', 'GatheredAccount']


class GatheredAccount(JMSOrgBaseModel):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_("Asset"))
    username = models.CharField(max_length=128, blank=True, db_index=True, verbose_name=_('Username'))
    address_last_login = models.CharField(null=True, max_length=45, default='', verbose_name=_("Address login"))
    date_last_login = models.DateTimeField(null=True, verbose_name=_("Date login"))
    remote_present = models.BooleanField(default=True, verbose_name=_("Remote present"))  # 远端资产上是否还存在
    present = models.BooleanField(default=False, verbose_name=_("Present"))  # 系统资产上是否还存在
    date_password_change = models.DateTimeField(null=True, verbose_name=_("Date change password"))
    date_password_expired = models.DateTimeField(null=True, verbose_name=_("Date password expired"))
    status = models.CharField(max_length=32, default=ConfirmOrIgnore.pending, blank=True,
                              choices=ConfirmOrIgnore.choices, verbose_name=_("Status"))
    detail = models.JSONField(default=dict, blank=True, verbose_name=_("Detail"))

    @property
    def address(self):
        return self.asset.address

    @classmethod
    def update_exists_accounts(cls, ga_accounts_set):  # gathered_account, accounts):
        to_updates = []

        for gathered_account, accounts in ga_accounts_set:
            if not gathered_account.date_last_login:
                return

            for account in accounts:
                # 这里是否可以考虑，标记成未从堡垒机登录风险 ？
                if not is_date_more_than(gathered_account.date_last_login, account.date_last_login, '5m'):
                    continue
                account.date_last_login = gathered_account.date_last_login
                account.login_by = '{}({})'.format('unknown', gathered_account.address_last_login)
                to_updates.append(account)

        Account.objects.bulk_update(to_updates, fields=['date_last_login', 'login_by'])

    @classmethod
    def bulk_create_accounts(cls, gathered_accounts):
        account_objs = []
        for gathered_account in gathered_accounts:
            asset_id = gathered_account.asset_id
            username = gathered_account.username
            account = Account(
                asset_id=asset_id, username=username,
                name=username, source=Source.DISCOVERY,
                date_last_login=gathered_account.date_last_login,
            )
            account_objs.append(account)
        Account.objects.bulk_create(account_objs, ignore_conflicts=True)

        ga_ids = [ga.id for ga in gathered_accounts]
        GatheredAccount.objects.filter(id__in=ga_ids).update(status=ConfirmOrIgnore.confirmed)

    @classmethod
    def sync_accounts(cls, gathered_accounts):
        """
        更新为已存在的账号，或者创建新的账号, 原来的 sync 重构了，如果存在则自动更新一些信息
        """
        assets = [gathered_account.asset_id for gathered_account in gathered_accounts]
        usernames = [gathered_account.username for gathered_account in gathered_accounts]

        origin_accounts = Account.objects.filter(
            asset__in=assets, username__in=usernames
        ).select_related('asset')

        origin_mapper = defaultdict(list)
        for origin_account in origin_accounts:
            asset_id = origin_account.asset_id
            username = origin_account.username
            origin_mapper[(asset_id, username)].append(origin_account)

        to_update = []
        to_create = []

        for gathered_account in gathered_accounts:
            asset_id = gathered_account.asset_id
            username = gathered_account.username
            accounts = origin_mapper.get((asset_id, username))

            if accounts:
                to_update.append((gathered_account, accounts))
            else:
                to_create.append(gathered_account)

        cls.bulk_create_accounts(to_create)
        cls.update_exists_accounts(to_update)

    class Meta:
        verbose_name = _("Gather asset accounts")
        unique_together = [
            ('username', 'asset'),
        ]
        ordering = ['asset']

    def __str__(self):
        return '{}: {}'.format(self.asset_id, self.username)


class GatherAccountsAutomation(AccountBaseAutomation):
    is_sync_account = models.BooleanField(
        default=False, blank=True, verbose_name=_("Is sync account")
    )
    recipients = models.ManyToManyField('users.User', verbose_name=_("Recipient"), blank=True)
    check_risk = models.BooleanField(default=True, verbose_name=_("Check risk"))

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'is_sync_account': self.is_sync_account,
            'check_risk': self.check_risk,
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
