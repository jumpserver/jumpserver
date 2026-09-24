"""Exclusive-branch workflow engine.

All transitions hold the instance row lock, and persist tasks and audit events in
the same transaction. Business adapters supply a trusted JSON context and consume
the resulting instance state; this module never provisions access or calls a
concrete ticket handler.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from orgs.models import Organization
from orgs.utils import current_org, tmp_to_org
from tickets.models import (
    Ticket, Workflow, WorkflowInstance, WorkflowNodeInstance, ApprovalTask, WorkflowEvent,
)
from .approvers import available_users, resolve_approvers, user_snapshot
from .conditions import evaluate_condition
from .const import InstanceState, NodeState, TaskState
from .definition import json_snapshot
from .errors import WorkflowConfigurationError, WorkflowConflict
from .signals import workflow_event
from tickets.plugins import get_ticket_plugin


class WorkflowEngine:
    @staticmethod
    def _check_org(org_id, allow_root=False):
        if not org_id or (org_id == Organization.ROOT_ID and not allow_root):
            raise WorkflowConfigurationError('Workflow instances must belong to a concrete organization.')
        if not current_org.is_root() and str(current_org.id) != str(org_id):
            raise PermissionDenied('This workflow belongs to another organization.')

    @staticmethod
    def _event(instance, event_type, *, node=None, task=None, actor=None, **data):
        event = WorkflowEvent.objects.create(
            instance=instance, type=event_type, node_instance=node, task=task,
            actor=actor, actor_snapshot=user_snapshot(actor), data=json_snapshot(data),
        )
        workflow_event.send(sender=WorkflowEngine, instance=instance, event=event)
        return event

    @transaction.atomic
    def start(self, ticket, workflow, context):
        self._check_org(ticket.org_id, allow_root=get_ticket_plugin(ticket.type).allow_global)
        # Serialize duplicate submission independently of which definition was selected.
        ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
        self._check_org(ticket.org_id, allow_root=get_ticket_plugin(ticket.type).allow_global)
        existing = WorkflowInstance.objects.filter(ticket=ticket).first()
        if existing:
            if existing.version.workflow_id != workflow.pk:
                raise WorkflowConflict('The ticket already has a different workflow.')
            return existing
        if ticket.ticket_steps.exists() or ticket.status != 'open':
            raise WorkflowConflict('Only new tickets without legacy approval steps can start a workflow.')
        # Root definitions can be used by any concrete organization. Resolve
        # approvers against the ticket organization, never the definition's org.
        from orgs.utils import tmp_to_root_org
        with tmp_to_root_org():
            workflow = Workflow.objects.select_for_update().get(pk=workflow.pk)
        if workflow.org_id not in (ticket.org_id, Organization.ROOT_ID):
            raise PermissionDenied('This workflow belongs to another organization.')
        version = workflow.active_version
        if not workflow.enabled or not version or not version.published_at or version.workflow_id != workflow.pk:
            raise WorkflowConfigurationError('Select an enabled workflow with a published version.')
        if ticket.type != workflow.type:
            raise WorkflowConfigurationError('The workflow type does not match the ticket.')
        snapshot = json_snapshot(context)
        if not isinstance(snapshot, dict):
            raise WorkflowConfigurationError('The context snapshot must be an object.')
        applicant = snapshot.setdefault('applicant', {})
        if not isinstance(applicant, dict) or not ticket.applicant_id:
            raise WorkflowConfigurationError('A workflow requires an applicant.')
        # Identity is authoritative; adapters may add department/manager metadata.
        applicant.update(user_snapshot(ticket.applicant))
        with tmp_to_org(ticket.org_id):
            instance = WorkflowInstance.objects.create(
                ticket=ticket, version=version, applicant=ticket.applicant,
                org_id=ticket.org_id,
                context=snapshot, state=InstanceState.running, date_started=timezone.now(),
            )
        self._event(instance, 'workflow.started', actor=ticket.applicant, version=version.number)
        self._advance(instance, version.nodes.get(type='start'))
        return instance

    def _lock_instance(self, instance_id):
        instance = WorkflowInstance.objects.select_for_update().get(pk=instance_id)
        self._check_org(instance.org_id, allow_root=get_ticket_plugin(instance.ticket.type).allow_global)
        return instance

    def _lock_task(self, task, actor):
        # Always lock in instance -> task order. The supplied task may be stale.
        instance_id = ApprovalTask.objects.values_list('node_instance__instance_id', flat=True).get(pk=task.pk)
        instance = self._lock_instance(instance_id)
        task = ApprovalTask.objects.select_related('node_instance__node').get(pk=task.pk)
        if instance.state != InstanceState.running or task.state != TaskState.pending:
            raise WorkflowConflict()
        if not actor or task.assignee_id != actor.pk or not available_users(instance.org_id).filter(pk=actor.pk).exists():
            raise PermissionDenied('Only the assigned, active organization member may process this task.')
        if task.node_instance.state != NodeState.running:
            raise WorkflowConflict()
        return instance, task

    def _advance(self, instance, node):
        try:
            with transaction.atomic():
                self._execute(instance, node)
        except WorkflowConfigurationError as exc:
            # Preserve the accepted vote and the diagnostic, without approving
            # a request whose next step cannot be evaluated or assigned.
            instance.refresh_from_db()
            self._finish(instance, InstanceState.error, detail=str(exc.detail))

    def _execute(self, instance, node):
        while node:
            run = WorkflowNodeInstance.objects.create(instance=instance, node=node)
            self._event(instance, 'node.entered', node=run, key=node.key, name=node.name)
            if node.type == 'approval':
                users = resolve_approvers(node.config, instance.context, instance.org_id, instance.applicant_id)
                strategy = node.config['strategy']
                run.required = len(users) if strategy == 'all' else node.config.get('required', 1)
                if run.required > len(users):
                    raise WorkflowConfigurationError('The quorum exceeds the number of eligible approvers.')
                if node.config['timeout']:
                    run.deadline = timezone.now() + timedelta(seconds=node.config['timeout'])
                run.save(update_fields=['required', 'deadline', 'date_updated'])
                for user in users:
                    self._create_task(instance, run, user)
                return
            result = None
            if node.type == 'condition':
                result = evaluate_condition(node.config, instance.context)
                run.result = {'condition': node.config, 'result': result}
                self._event(instance, 'condition.evaluated', node=run, **run.result)
            elif node.type == 'cc':
                configured = node.config['users']
                users = list(available_users(instance.org_id).filter(pk__in=configured).order_by('id'))
                existing = set(instance.ticket.cc_users.values_list('pk', flat=True))
                added = [user for user in users if user.pk not in existing]
                if added:
                    instance.ticket.cc_users.add(*added)
                run.result = {'recipients': [user_snapshot(user) for user in added]}
                self._event(instance, 'cc.added', node=run, **run.result)
            self._complete_node(instance, run)
            if node.type == 'end':
                self._finish(instance, InstanceState.approved)
                return
            edge = node.outgoing.get(condition=result)
            node = edge.target

    def _create_task(self, instance, node, user, *, predecessor=None, is_added=False, actor=None):
        task = ApprovalTask.objects.create(
            node_instance=node, assignee=user, assignee_snapshot=user_snapshot(user),
            predecessor=predecessor, is_added=is_added,
        )
        self._event(instance, 'approval.created', node=node, task=task, actor=actor,
                    assignee=task.assignee_snapshot, is_added=is_added)
        return task

    def _complete_node(self, instance, run):
        run.state = NodeState.approved
        run.date_finished = timezone.now()
        run.save(update_fields=['state', 'date_finished', 'result', 'date_updated'])
        self._event(instance, 'node.completed', node=run, state=run.state)

    def _close_pending(self, instance, *, node=None, state=TaskState.cancelled):
        tasks = ApprovalTask.objects.filter(node_instance__instance=instance, state=TaskState.pending)
        if node:
            tasks = tasks.filter(node_instance=node)
        for task in tasks:
            task.state, task.date_finished = state, timezone.now()
            task.save(update_fields=['state', 'date_finished', 'date_updated'])
            self._event(instance, f'approval.{state}', node=task.node_instance, task=task)

    def _finish(self, instance, state, *, actor=None, **data):
        self._close_pending(instance, state=TaskState.expired if state == InstanceState.expired else TaskState.cancelled)
        for run in instance.node_instances.filter(state=NodeState.running):
            run.state = NodeState.rejected if state == InstanceState.rejected else NodeState.cancelled
            run.date_finished = timezone.now()
            run.save(update_fields=['state', 'date_finished', 'date_updated'])
            self._event(instance, 'node.completed', node=run, state=run.state)
        visited = instance.node_instances.values_list('node_id', flat=True)
        WorkflowNodeInstance.objects.bulk_create([
            WorkflowNodeInstance(instance=instance, node=node, state=NodeState.skipped, date_finished=timezone.now())
            for node in instance.version.nodes.exclude(pk__in=visited)
        ])
        instance.state, instance.date_finished = state, timezone.now()
        with tmp_to_org(instance.org_id):
            instance.save(update_fields=['state', 'date_finished', 'date_updated'])
        event = {'cancelled': 'workflow.cancelled', 'expired': 'workflow.expired', 'error': 'workflow.error'}.get(state, 'workflow.completed')
        self._event(instance, event, actor=actor, state=state, **data)

    def _expire_if_due(self, instance, run):
        if run.deadline and run.deadline <= timezone.now():
            self._event(instance, 'approval.timed_out', node=run, deadline=run.deadline.isoformat())
            self._close_pending(instance, node=run, state=TaskState.expired)
            state = InstanceState.rejected if run.node.config['timeout_action'] == 'reject' else InstanceState.expired
            self._finish(instance, state)
            return True
        return False

    @transaction.atomic
    def approve(self, task, user, comment=''):
        instance, task = self._lock_task(task, user)
        run = task.node_instance
        if self._expire_if_due(instance, run):
            return instance
        task.state, task.comment, task.date_finished = TaskState.approved, comment, timezone.now()
        task.save(update_fields=['state', 'comment', 'date_finished', 'date_updated'])
        self._event(instance, 'approval.approved', node=run, task=task, actor=user, comment=comment)
        votes = run.tasks.filter(state=TaskState.approved, is_added=False).count()
        added_pending = run.tasks.filter(is_added=True, state=TaskState.pending).exists()
        if votes >= run.required and not added_pending:
            self._close_pending(instance, node=run)
            self._complete_node(instance, run)
            self._advance(instance, run.node.outgoing.get().target)
        return instance

    @transaction.atomic
    def reject(self, task, user, comment=''):
        instance, task = self._lock_task(task, user)
        if self._expire_if_due(instance, task.node_instance):
            return instance
        task.state, task.comment, task.date_finished = TaskState.rejected, comment, timezone.now()
        task.save(update_fields=['state', 'comment', 'date_finished', 'date_updated'])
        self._event(instance, 'approval.rejected', node=task.node_instance, task=task, actor=user, comment=comment)
        self._finish(instance, InstanceState.rejected, actor=user)
        return instance

    @transaction.atomic
    def cancel(self, instance, user, comment=''):
        instance = self._lock_instance(instance.pk)
        if not user or instance.applicant_id != user.pk:
            raise PermissionDenied('Only the applicant may withdraw this workflow.')
        if instance.state != InstanceState.running:
            raise WorkflowConflict()
        run = instance.node_instances.select_related('node').get(state=NodeState.running)
        if not self._expire_if_due(instance, run):
            self._finish(instance, InstanceState.cancelled, actor=user, comment=comment)
        return instance

    def _target_user(self, instance, run, target):
        if not available_users(instance.org_id).filter(pk=target.pk).exists():
            raise WorkflowConfigurationError('The target must be an active member of this organization.')
        if run.node.config['exclude_applicant'] and target.pk == instance.applicant_id:
            raise WorkflowConfigurationError('The applicant cannot approve this node.')
        if run.tasks.filter(assignee=target).exists():
            raise WorkflowConfigurationError('The target already participated in this approval node.')
        if run.tasks.count() >= 1000:
            raise WorkflowConfigurationError('An approval node supports at most 1000 tasks.')

    @transaction.atomic
    def transfer(self, task, user, target, comment=''):
        instance, task = self._lock_task(task, user)
        run = task.node_instance
        if not run.node.config['allow_transfer']:
            raise PermissionDenied('Transfer is disabled for this node.')
        if self._expire_if_due(instance, run):
            return instance
        self._target_user(instance, run, target)
        task.state, task.comment, task.date_finished = TaskState.transferred, comment, timezone.now()
        task.save(update_fields=['state', 'comment', 'date_finished', 'date_updated'])
        replacement = self._create_task(instance, run, target, predecessor=task, is_added=task.is_added, actor=user)
        self._event(instance, 'approval.transferred', node=run, task=task, actor=user,
                    target=replacement.assignee_snapshot, replacement=str(replacement.pk), comment=comment)
        return instance

    @transaction.atomic
    def add_approver(self, task, user, target, comment=''):
        instance, task = self._lock_task(task, user)
        run = task.node_instance
        if not run.node.config['allow_add_approver']:
            raise PermissionDenied('Adding approvers is disabled for this node.')
        if self._expire_if_due(instance, run):
            return instance
        self._target_user(instance, run, target)
        added = self._create_task(instance, run, target, predecessor=task, is_added=True, actor=user)
        self._event(instance, 'approval.added', node=run, task=added, actor=user,
                    target=added.assignee_snapshot, comment=comment)
        return instance

    @transaction.atomic
    def expire(self, instance):
        instance = self._lock_instance(instance.pk)
        if instance.state == InstanceState.running:
            run = instance.node_instances.select_related('node').filter(state=NodeState.running).first()
            if run:
                self._expire_if_due(instance, run)
        return instance
