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
        ]

    def start(self):
        from accounts.automations.endpoint import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager.run()


class ChangeSecretMixin(SecretWithRandomMixin):
    ssh_key_change_strategy = models.CharField(
        choices=SSHKeyStrategy.choices, max_length=16,
        default=SSHKeyStrategy.add, verbose_name=_('SSH key change strategy')
    )
    get_all_assets: callable  # get all assets

    class Meta:
        abstract = True

    def create_nonlocal_accounts(self, usernames, asset):
        pass

    def get_account_ids(self):
        usernames = self.accounts
        accounts = Account.objects.none()
        for asset in self.get_all_assets():
            self.create_nonlocal_accounts(usernames, asset)
            accounts = accounts | asset.accounts.all()
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
        })
        return attr_json
