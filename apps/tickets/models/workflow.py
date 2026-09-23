from contextlib import contextmanager

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from orgs.mixins.models import JMSOrgBaseModel
from tickets.const import TicketType
from tickets.workflow.const import NodeType

__all__ = ['Workflow', 'WorkflowVersion', 'WorkflowNode', 'WorkflowEdge']


class Workflow(JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    type = models.CharField(max_length=64, choices=TicketType.choices, verbose_name=_('Type'))
    enabled = models.BooleanField(default=False, verbose_name=_('Enabled'))
    is_system = models.BooleanField(default=False, editable=False)
    cc_users = models.ManyToManyField('users.User', blank=True, related_name='+', verbose_name=_('CC users'))
    active_version = models.ForeignKey(
        'WorkflowVersion', null=True, blank=True, on_delete=models.PROTECT,
        related_name='+', editable=False,
    )
    # Used only by the one-off importer, never to execute a legacy definition.
    legacy_flow_id = models.UUIDField(null=True, unique=True, editable=False)
    migration_notes = models.JSONField(default=dict, editable=False)

    class Meta:
        verbose_name = _('Approval workflow')
        default_permissions = ('add', 'change', 'view')
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['org_id', 'type', 'name'], name='tickets_workflow_org_name_uniq'),
        ]

    def __str__(self):
        return self.name


@contextmanager
def editable_versions(version_ids, using):
    """Serialize graph writes with publication, including bulk ORM writes."""
    with transaction.atomic(using=using):
        versions = list(WorkflowVersion.objects.using(using).select_for_update().filter(pk__in=version_ids))
        if any(version.published_at is not None for version in versions):
            raise ValidationError(_('Published workflow versions are immutable. Create a new version.'))
        yield


class DefinitionQuerySet(models.QuerySet):
    def version_ids(self):
        field = 'pk' if self.model.__name__ == 'WorkflowVersion' else 'version_id'
        return list(self.values_list(field, flat=True))

    def update(self, **kwargs):
        if {'version', 'version_id', 'workflow', 'workflow_id', 'published_at'} & kwargs.keys():
            raise ValidationError(_('Workflow definition identity cannot be updated in bulk.'))
        with editable_versions(self.version_ids(), self.db):
            return super().update(**kwargs)

    def delete(self):
        with editable_versions(self.version_ids(), self.db):
            return super().delete()

    def bulk_create(self, objs, **kwargs):
        objs = list(objs)
        if self.model.__name__ == 'WorkflowVersion':
            raise ValidationError(_('Create workflow versions through the publication service.'))
        if kwargs.get('update_conflicts'):
            raise ValidationError(_('Workflow definitions do not support upserts.'))
        with editable_versions([obj.version_id for obj in objs], self.db):
            for obj in objs:
                obj.clean()
            return super().bulk_create(objs, **kwargs)


class DefinitionModel(JMSBaseModel):
    objects = DefinitionQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or self._state.db or 'default'
        is_version = isinstance(self, WorkflowVersion)
        old = type(self).objects.using(using).filter(pk=self.pk).first()
        if old:
            identity = ('workflow_id', 'number') if is_version else ('version_id',)
            if any(getattr(old, field) != getattr(self, field) for field in identity):
                raise ValidationError(_('Workflow definition identity cannot be changed.'))
        ids = [self.pk] if is_version else [self.version_id]
        with editable_versions(ids, using):
            self.clean()
            return super().save(*args, **kwargs)

    def delete(self, using=None, **kwargs):
        return type(self).objects.using(using or self._state.db).filter(pk=self.pk).delete()


class WorkflowVersion(DefinitionModel):
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name='versions')
    number = models.PositiveIntegerField()
    published_at = models.DateTimeField(null=True, editable=False)

    class Meta:
        verbose_name = _('Workflow version')
        default_permissions = ()
        ordering = ['-number']
        constraints = [
            models.UniqueConstraint(fields=['workflow', 'number'], name='tickets_workflow_version_uniq'),
        ]

    def as_definition(self):
        return {
            'nodes': [
                {'id': node.key, 'type': node.type, 'name': node.name, 'config': node.config,
                 'position': {'x': node.position_x, 'y': node.position_y}}
                for node in self.nodes.order_by('key')
            ],
            'edges': [
                {'source': edge.source.key, 'target': edge.target.key,
                 'condition': edge.condition, 'priority': edge.priority}
                for edge in self.edges.select_related('source', 'target').order_by('priority', 'id')
            ],
        }


class WorkflowNode(DefinitionModel):
    version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name='nodes')
    key = models.CharField(max_length=64)
    type = models.CharField(max_length=16, choices=NodeType.choices)
    name = models.CharField(max_length=128, blank=True)
    config = models.JSONField(default=dict)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)

    class Meta:
        verbose_name = _('Workflow node')
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(fields=['version', 'key'], name='tickets_workflow_node_key_uniq'),
        ]


class WorkflowEdge(DefinitionModel):
    version = models.ForeignKey(WorkflowVersion, on_delete=models.CASCADE, related_name='edges')
    source = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name='outgoing')
    target = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name='incoming')
    condition = models.BooleanField(null=True)
    priority = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('Workflow edge')
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(fields=['version', 'source', 'target'], name='tickets_workflow_edge_uniq'),
        ]

    def clean(self):
        super().clean()
        if self.source.version_id != self.version_id or self.target.version_id != self.version_id:
            raise ValidationError(_('Workflow edges must connect nodes in the same version.'))
