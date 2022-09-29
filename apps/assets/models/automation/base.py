import uuid
from celery import current_task
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.const.choices import Trigger
from common.mixins.models import CommonModelMixin
from common.db.fields import EncryptJsonDictTextField
from orgs.mixins.models import OrgModelMixin
from ops.mixin import PeriodTaskModelMixin
from ops.tasks import execute_automation_strategy
from ops.task_handlers import ExecutionManager


class BaseAutomation(CommonModelMixin, PeriodTaskModelMixin, OrgModelMixin):
    accounts = models.JSONField(default=list, verbose_name=_("Accounts"))
    nodes = models.ManyToManyField(
        'assets.Node', related_name='automation_strategy', blank=True, verbose_name=_("Nodes")
    )
    assets = models.ManyToManyField(
        'assets.Asset', related_name='automation_strategy', blank=True, verbose_name=_("Assets")
    )
    type = models.CharField(max_length=16, verbose_name=_('Type'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name + '@' + str(self.created_by)

    def get_register_task(self):
        name = "automation_strategy_period_{}".format(str(self.id)[:8])
        task = execute_automation_strategy.name
        args = (str(self.id), Trigger.timing)
        kwargs = {}
        return name, task, args, kwargs

    def to_attr_json(self):
        return {
            'name': self.name,
            'accounts': self.accounts,
            'assets': list(self.assets.all().values_list('id', flat=True)),
            'nodes': list(self.assets.all().values_list('id', flat=True)),
        }

    def execute(self, trigger):
        try:
            eid = current_task.request.id
        except AttributeError:
            eid = str(uuid.uuid4())
        execution = AutomationStrategyExecution.objects.create(
            id=eid, strategy=self, snapshot=self.to_attr_json(), trigger=trigger
        )
        return execution.start()

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Automation plan")


class AutomationStrategyExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)

    date_created = models.DateTimeField(auto_now_add=True)
    timedelta = models.FloatField(default=0.0, verbose_name=_('Time'), null=True)
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Date start'))

    snapshot = EncryptJsonDictTextField(
        default=dict, blank=True, null=True, verbose_name=_('Automation snapshot')
    )
    strategy = models.ForeignKey(
        'assets.models.automation.base.BaseAutomation', related_name='execution', on_delete=models.CASCADE,
        verbose_name=_('Automation strategy')
    )
    trigger = models.CharField(
        max_length=128, default=Trigger.manual, choices=Trigger.choices, verbose_name=_('Trigger mode')
    )

    class Meta:
        verbose_name = _('Automation strategy execution')

    @property
    def manager_type(self):
        return self.snapshot['type']

    def start(self):
        manager = ExecutionManager(execution=self)
        return manager.run()


class AutomationStrategyTask(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset')
    )
    account = models.ForeignKey(
        'assets.Account', on_delete=models.CASCADE, verbose_name=_('Account')
    )
    is_success = models.BooleanField(default=False, verbose_name=_('Is success'))
    timedelta = models.FloatField(default=0.0, null=True, verbose_name=_('Time'))
    date_start = models.DateTimeField(auto_now_add=True, verbose_name=_('Date start'))
    reason = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_('Reason'))
    execution = models.ForeignKey(
        'AutomationStrategyExecution', related_name='task', on_delete=models.CASCADE,
        verbose_name=_('Automation strategy execution')
    )

    class Meta:
        verbose_name = _('Automation strategy task')

    @property
    def handler_type(self):
        return self.execution.snapshot['type']
