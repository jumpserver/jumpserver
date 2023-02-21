from django.utils.translation import gettext_lazy as _

from accounts.tasks import execute_account_automation_task
from assets.models.automations import (
    BaseAutomation as AssetBaseAutomation,
    AutomationExecution as AssetAutomationExecution
)

__all__ = ['AccountBaseAutomation', 'AutomationExecution']


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
            ('add_changesecretexection', _('Can add change secret execution')),

            ('view_gatheraccountsexecution', _('Can view gather accounts execution')),
            ('add_gatheraccountsexecution', _('Can add gather accounts execution')),

            ('view_pushaccountexecution', _('Can view push account execution')),
            ('add_pushaccountexecution', _('Can add push account execution')),
        ]

    def start(self):
        from accounts.automations.endpoint import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager.run()
