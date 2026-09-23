from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from orgs.mixins.models import JMSOrgBaseModel, OrgManager
from tickets.workflow.const import InstanceState, NodeState, TaskState

__all__ = ['WorkflowInstance', 'WorkflowNodeInstance', 'ApprovalTask', 'WorkflowEvent']


class InstanceQuerySet(models.QuerySet):
    frozen_fields = {'context', 'version', 'version_id', 'ticket', 'ticket_id', 'org_id'}

    def update(self, **kwargs):
        if self.frozen_fields & kwargs.keys():
            raise ValidationError(_('Workflow context and identity are immutable.'))
        return super().update(**kwargs)


class WorkflowInstance(JMSOrgBaseModel):
    ticket = models.OneToOneField('Ticket', on_delete=models.PROTECT, related_name='workflow_instance')
    version = models.ForeignKey('WorkflowVersion', on_delete=models.PROTECT, related_name='instances')
    applicant = models.ForeignKey('users.User', null=True, on_delete=models.SET_NULL, related_name='+')
    context = models.JSONField(default=dict, editable=False)
    state = models.CharField(max_length=16, choices=InstanceState.choices, default=InstanceState.pending)
    date_started = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)
    objects = OrgManager.from_queryset(InstanceQuerySet)()

    def save(self, *args, **kwargs):
        fields = ('context', 'version_id', 'ticket_id', 'org_id')
        updates = kwargs.get('update_fields')
        if not self._state.adding and (updates is None or InstanceQuerySet.frozen_fields.intersection(updates)):
            original = type(self)._base_manager.get(pk=self.pk)
            if any(getattr(original, field) != getattr(self, field) for field in fields):
                raise ValidationError(_('Workflow context and identity are immutable.'))
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Workflow instance')
        ordering = ['-date_created', 'id']
        default_permissions = ('view',)


class WorkflowNodeInstance(JMSBaseModel):
    instance = models.ForeignKey(WorkflowInstance, on_delete=models.PROTECT, related_name='node_instances')
    node = models.ForeignKey('WorkflowNode', on_delete=models.PROTECT, related_name='instances')
    state = models.CharField(max_length=16, choices=NodeState.choices, default=NodeState.running)
    required = models.PositiveIntegerField(default=0)
    deadline = models.DateTimeField(null=True, db_index=True)
    date_finished = models.DateTimeField(null=True)
    result = models.JSONField(default=dict)

    class Meta:
        verbose_name = _('Workflow node instance')
        ordering = ['date_created', 'id']
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(fields=['instance', 'node'], name='tickets_workflow_node_run_uniq'),
        ]


class ApprovalTask(JMSBaseModel):
    node_instance = models.ForeignKey(WorkflowNodeInstance, on_delete=models.PROTECT, related_name='tasks')
    assignee = models.ForeignKey('users.User', null=True, on_delete=models.SET_NULL, related_name='approval_tasks')
    assignee_snapshot = models.JSONField(default=dict, editable=False)
    state = models.CharField(max_length=16, choices=TaskState.choices, default=TaskState.pending)
    # An added approver is mandatory, independently of the original threshold.
    is_added = models.BooleanField(default=False)
    predecessor = models.ForeignKey('self', null=True, on_delete=models.PROTECT, related_name='successors')
    date_finished = models.DateTimeField(null=True)

    class Meta:
        verbose_name = _('Approval task')
        default_permissions = ()
        ordering = ['date_created', 'id']
        constraints = [
            models.UniqueConstraint(fields=['node_instance', 'assignee'], name='tickets_approval_task_user_uniq'),
        ]
        indexes = [models.Index(fields=['assignee', 'state'], name='tickets_task_assignee_state')]


class WorkflowEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    instance = models.ForeignKey(WorkflowInstance, on_delete=models.PROTECT, related_name='events')
    node_instance = models.ForeignKey(WorkflowNodeInstance, null=True, on_delete=models.PROTECT, related_name='+')
    task = models.ForeignKey(ApprovalTask, null=True, on_delete=models.PROTECT, related_name='+')
    type = models.CharField(max_length=64)
    actor = models.ForeignKey('users.User', null=True, on_delete=models.SET_NULL, related_name='+')
    actor_snapshot = models.JSONField(default=dict, editable=False)
    data = models.JSONField(default=dict)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Workflow event')
        default_permissions = ()
        ordering = ['id']
