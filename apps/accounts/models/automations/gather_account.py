from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes, Source
from accounts.models import Account
from orgs.mixins.models import JMSOrgBaseModel
from .base import AccountBaseAutomation

__all__ = ['GatherAccountsAutomation', 'GatheredAccount']


class GatheredAccount(JMSOrgBaseModel):
    present = models.BooleanField(default=True, verbose_name=_("Present"))
    date_last_login = models.DateTimeField(null=True, verbose_name=_("Date last login"))
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_("Asset"))
    username = models.CharField(max_length=32, blank=True, db_index=True, verbose_name=_('Username'))
    address_last_login = models.CharField(max_length=39, default='', verbose_name=_("Address last login"))

    @property
    def address(self):
        return self.asset.address

    @staticmethod
    def sync_accounts(gathered_accounts):
        account_objs = []
        for gathered_account in gathered_accounts:
            asset_id = gathered_account.asset_id
            username = gathered_account.username
            accounts = Account.objects.filter(
                Q(asset_id=asset_id, username=username) |
                Q(asset_id=asset_id, name=username)
            )
            if accounts.exists():
                continue
            account = Account(
                asset_id=asset_id, username=username,
                name=username, source=Source.COLLECTED
            )
            account_objs.append(account)
        Account.objects.bulk_create(account_objs)

    class Meta:
        verbose_name = _('Gather account automation')
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
        verbose_name = _("Gather asset accounts")
