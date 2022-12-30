from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.models.automations import (
    BaseAutomation as AssetBaseAutomation,
    AutomationExecution as AssetAutomationExecution
)

__all__ = ['AccountBaseAutomation', 'AutomationExecution']


class AccountBaseAutomation(AssetBaseAutomation):
    class Meta:
        proxy = True
        verbose_name = _("Account automation task")

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'accounts': self.accounts
        })
        return attr_json


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
        ]
