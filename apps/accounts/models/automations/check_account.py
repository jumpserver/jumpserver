from django.db import models
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from common.const import Trigger
from orgs.mixins.models import JMSOrgBaseModel
from .base import AccountBaseAutomation
from ...const import AutomationTypes

__all__ = ['AccountCheckAutomation', 'AccountRisk']


class AccountCheckAutomation(AccountBaseAutomation):

    def get_register_task(self):
        from ...tasks import check_accounts_task
        name = "check_accounts_task_period_{}".format(str(self.id)[:8])
        task = check_accounts_task.name
        args = (str(self.id), Trigger.timing)
        kwargs = {}
        return name, task, args, kwargs

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
        })
        return attr_json

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.check_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Gather account automation')


class RiskChoice(TextChoices):
    zombie = 'zombie', _('Zombie')  # 好久没登录的账号
    ghost = 'ghost', _('Ghost')  # 未被纳管的账号
    weak_password = 'weak_password', _('Weak password')
    longtime_no_change = 'long_time_no_change', _('Long time no change')


class AccountRisk(JMSOrgBaseModel):
    account = models.ForeignKey('Account', on_delete=models.CASCADE, related_name='risks', verbose_name=_('Account'))
    risk = models.CharField(max_length=128, verbose_name=_('Risk'), choices=RiskChoice.choices)
    confirmed = models.BooleanField(default=False, verbose_name=_('Confirmed'))

    class Meta:
        verbose_name = _('Account risk')

    def __str__(self):
        return f"{self.account} - {self.risk}"
