import uuid

from celery import current_task
from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.models.asset import Asset
from assets.models.node import Node
from assets.tasks import execute_asset_automation_task
from common.const.choices import Trigger
from common.db.fields import EncryptJsonDictTextField
from ops.mixin import PeriodTaskModelMixin
from orgs.mixins.models import OrgModelMixin, JMSOrgBaseModel


class BaseAutomation(PeriodTaskModelMixin, JMSOrgBaseModel):
    accounts = models.JSONField(default=list, verbose_name=_("Accounts"))
    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Node"))
    assets = models.ManyToManyField('assets.Asset', blank=True, verbose_name=_("Assets"))
    type = models.CharField(max_length=16, verbose_name=_('Type'))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    params = models.JSONField(default=dict, verbose_name=_("Parameters"))

    def __str__(self):
        return self.name + '@' + str(self.created_by)

    class Meta:
        unique_together = [('org_id', 'name', 'type')]
        verbose_name = _("Automation task")

    @classmethod
    def generate_unique_name(cls, name):
        while True:
            name = name + str(uuid.uuid4())[:8]
            try:
                cls.objects.get(name=name)
            except cls.DoesNotExist:
                return name

    def get_all_assets(self):
        nodes = self.nodes.all()
        node_asset_ids = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
        direct_asset_ids = self.assets.all().values_list('id', flat=True)
        asset_ids = set(list(direct_asset_ids) + list(node_asset_ids))
        return Asset.objects.filter(id__in=asset_ids)

    def all_assets_group_by_platform(self):
        assets = self.get_all_assets().prefetch_related('platform')
        return assets.group_by_platform()

    @property
    def execute_task(self):
        return execute_asset_automation_task

    def get_register_task(self):
        name = f"automation_{self.type}_strategy_period_{str(self.id)[:8]}"
        task = self.execute_task.name
        args = (str(self.id), Trigger.timing, self.type)
        kwargs = {}
        return name, task, args, kwargs

    def get_many_to_many_ids(self, field: str):
        return [str(i) for i in getattr(self, field).all().values_list('id', flat=True)]

    def to_attr_json(self):
        return {
            'name': self.name,
            'type': self.type,
            'comment': self.comment,
            'accounts': self.accounts,
            'org_id': str(self.org_id),
            'nodes': self.get_many_to_many_ids('nodes'),
            'assets': self.get_many_to_many_ids('assets'),
        }

    @property
    def execution_model(self):
        return AutomationExecution

    @property
    def executed_amount(self):
        return self.executions.count()

    @property
    def latest_execution(self):
        return self.executions.first()

    def execute(self, trigger=Trigger.manual):
        try:
            eid = current_task.request.id
        except AttributeError:
            eid = str(uuid.uuid4())

        execution = self.execution_model.objects.create(
            id=eid, trigger=trigger, automation=self,
            snapshot=self.to_attr_json(),
        )
        return execution.start()


class AssetBaseAutomation(BaseAutomation):
    class Meta:
        proxy = True
        verbose_name = _("Asset automation task")


class AutomationExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    automation = models.ForeignKey(
        'BaseAutomation', related_name='executions', on_delete=models.CASCADE,
        verbose_name=_('Automation task'), null=True
    )
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))
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
        ordering = ('-date_start',)
        verbose_name = _('Automation task execution')

    @property
    def manager_type(self):
        return self.snapshot['type']

    def get_all_asset_ids(self):
        node_ids = self.snapshot['nodes']
        asset_ids = self.snapshot['assets']
        nodes = Node.objects.filter(id__in=node_ids)
        node_asset_ids = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
        asset_ids = set(list(asset_ids) + list(node_asset_ids))
        return asset_ids

    def get_all_assets(self):
        asset_ids = self.get_all_asset_ids()
        return Asset.objects.filter(id__in=asset_ids)

    def all_assets_group_by_platform(self):
        assets = self.get_all_assets().prefetch_related('platform')
        return assets.group_by_platform()

    @property
    def recipients(self):
        recipients = self.snapshot.get('recipients')
        if not recipients:
            return {}
        return recipients

    def start(self):
        from assets.automations.endpoint import ExecutionManager
        manager = ExecutionManager(execution=self)
        return manager.run()
