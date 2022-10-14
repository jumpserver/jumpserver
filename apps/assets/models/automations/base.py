import uuid
from celery import current_task
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.const.choices import Trigger
from common.db.fields import EncryptJsonDictTextField
from orgs.mixins.models import OrgModelMixin, JMSOrgBaseModel
from ops.mixin import PeriodTaskModelMixin
from ops.tasks import execute_automation_strategy
from assets.models import Node, Asset


class AutomationTypes(models.TextChoices):
    ping = 'ping', _('Ping')
    gather_facts = 'gather_facts', _('Gather facts')
    create_account = 'create_account', _('Create account')
    change_secret = 'change_secret', _('Change secret')
    verify_account = 'verify_account', _('Verify account')
    gather_accounts = 'gather_accounts', _('Gather accounts')


class BaseAutomation(JMSOrgBaseModel, PeriodTaskModelMixin):
    accounts = models.JSONField(default=list, verbose_name=_("Accounts"))
    nodes = models.ManyToManyField(
        'assets.Node', blank=True, verbose_name=_("Nodes")
    )
    assets = models.ManyToManyField(
        'assets.Asset', blank=True, verbose_name=_("Assets")
    )
    type = models.CharField(max_length=16, verbose_name=_('Type'))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name + '@' + str(self.created_by)

    def get_all_assets(self):
        nodes = self.nodes.all()
        node_asset_ids = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
        direct_asset_ids = self.assets.all().values_list('id', flat=True)
        asset_ids = set(list(direct_asset_ids) + list(node_asset_ids))
        return Asset.objects.filter(id__in=asset_ids)

    def all_assets_group_by_platform(self):
        assets = self.get_all_assets().prefetch_related('platform')
        return assets.group_by_platform()

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

    def execute(self, trigger=Trigger.manual):
        try:
            eid = current_task.request.id
        except AttributeError:
            eid = str(uuid.uuid4())

        execution = self.executions.create(
            id=eid, trigger=trigger,
        )
        return execution.start()

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Automation plan")


class AutomationExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    automation = models.ForeignKey(
        'BaseAutomation', related_name='executions', on_delete=models.CASCADE,
        verbose_name=_('Automation strategy')
    )
    status = models.CharField(max_length=16, default='pending')
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'), db_index=True)
    date_finished = models.DateTimeField(null=True, verbose_name=_("Date finished"))
    snapshot = EncryptJsonDictTextField(
        default=dict, blank=True, null=True, verbose_name=_('Automation snapshot')
    )
    trigger = models.CharField(
        max_length=128, default=Trigger.manual, choices=Trigger.choices,
        verbose_name=_('Trigger mode')
    )

    class Meta:
        verbose_name = _('Automation strategy execution')

    @property
    def manager_type(self):
        return self.snapshot['type']

    def start(self):
        from assets.automations.endpoint import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager.run()
