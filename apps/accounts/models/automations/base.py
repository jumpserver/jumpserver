from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.const import SSHKeyStrategy
from accounts.models import Account, SecretWithRandomMixin
from accounts.tasks import execute_account_automation_task
from assets.models.automations import (
    BaseAutomation as AssetBaseAutomation,
    AutomationExecution as AssetAutomationExecution
)

__all__ = ['AccountBaseAutomation', 'AutomationExecution', 'ChangeSecretMixin']


class AccountBaseAutomation(AssetBaseAutomation):
    class Meta:
        proxy = True
        verbose_name = _("Account automation task")

    @property
    def execute_task(self):
        return execute_account_automation_task

    @property
    def execution_model(self):
        return AutomationExecution


class AutomationExecution(AssetAutomationExecution):
    class Meta:
        proxy = True
        verbose_name = _("Automation execution")
        verbose_name_plural = _("Automation executions")
        permissions = [
            ('view_changesecretexecution', _('Can view change secret execution')),
            ('add_changesecretexecution', _('Can add change secret execution')),

            ('view_gatheraccountsexecution', _('Can view gather accounts execution')),
            ('add_gatheraccountsexecution', _('Can add gather accounts execution')),

            ('view_pushaccountexecution', _('Can view push account execution')),
            ('add_pushaccountexecution', _('Can add push account execution')),

            ('view_backupaccountexecution', _('Can view backup account execution')),
            ('add_backupaccountexecution', _('Can add backup account execution')),
        ]

    @property
    def manager(self):
        from accounts.automations.endpoint import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager


class ChangeSecretMixin(SecretWithRandomMixin):
    ssh_key_change_strategy = models.CharField(
        choices=SSHKeyStrategy.choices,
        max_length=16,
        default=SSHKeyStrategy.set_jms,
        verbose_name=_('SSH key change strategy')
    )
    check_conn_after_change = models.BooleanField(
        default=True,
        verbose_name=_('Check connection after change')
    )
    get_all_assets: callable  # get all assets
    accounts: list  # account usernames

    class Meta:
        abstract = True

    def gen_nonlocal_accounts(self, usernames, asset):
        return []

    def get_account_ids(self):
        account_objs = []
        usernames = self.accounts
        assets = self.get_all_assets()
        for asset in assets:
            objs = self.gen_nonlocal_accounts(usernames, asset)
            account_objs.extend(objs)

        Account.objects.bulk_create(account_objs)

        accounts = Account.objects.filter(asset__in=assets)
        account_ids = accounts.filter(
            username__in=usernames, secret_type=self.secret_type
        ).values_list('id', flat=True)
        return [str(_id) for _id in account_ids]

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'secret': self.secret,
            'secret_type': self.secret_type,
            'accounts': self.get_account_ids(),
            'password_rules': self.password_rules,
            'secret_strategy': self.secret_strategy,
            'ssh_key_change_strategy': self.ssh_key_change_strategy,
            'check_conn_after_change': self.check_conn_after_change,
        })
        return attr_json
