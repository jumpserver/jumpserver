"""Ticket adapters: trusted input snapshots, atomic effects and notifications."""
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone

from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.const import TicketOrigin
from tickets.models import Ticket, Workflow
from .approvers import available_users, user_snapshot
from tickets.plugins import get_ticket_plugin
from .errors import WorkflowConfigurationError
from .signals import workflow_event


def build_context(ticket):
    plugin = get_ticket_plugin(ticket.type)
    applicant = user_snapshot(ticket.applicant)
    applicant['manager_id'] = str(ticket.applicant.manager_id) if ticket.applicant.manager_id else None
    with tmp_to_org(ticket.org_id):
        context = plugin.build_context(ticket)
    context.setdefault('request', {}).update(type=ticket.type, title=ticket.title)
    context['applicant'] = applicant
    context['plugin'] = {'type': plugin.type, 'execution_mode': plugin.execution_mode}
    for key in ('assets', 'accounts', 'nodes'):
        context.setdefault(key, [])
    return context


@transaction.atomic
def submit_ticket(ticket):
    from .engine import WorkflowEngine
    if not ticket.workflow_id:
        raise WorkflowConfigurationError('Select a published workflow.')
    if not ticket.applicant_id or not available_users(ticket.org_id).filter(pk=ticket.applicant_id).exists():
        raise WorkflowConfigurationError('The applicant must be an active organization member.')
    ticket.set_serial_num()
    ticket.set_rel_snapshot()
    context = build_context(ticket)
    instance = WorkflowEngine().start(ticket, ticket.workflow, context)
    # Configuration failures on submission must not leave unusable open tickets.
    if instance.state == 'error':
        event = instance.events.filter(type='workflow.error').last()
        raise WorkflowConfigurationError(event.data.get('detail', 'Invalid workflow configuration.'))
    ticket.refresh_from_db()
    return instance


@transaction.atomic
def submit_system_ticket(ticket, assignees, workflow=None):
    """ACLs without a selected workflow get a versioned one-node definition.

    Existing ACL reviewer configuration remains a useful simple authoring form;
    it creates exactly the same task/instance model as the visual designer.
    """
    from .publication import publish_workflow
    if workflow is None:
        import hashlib
        ids = sorted(str(user.pk) for user in assignees)
        if not ids:
            raise WorkflowConfigurationError('Configure reviewers or select a workflow on the ACL.')
        digest = hashlib.sha256(','.join(ids).encode()).hexdigest()[:24]
        with tmp_to_org(ticket.org_id):
            workflow, _ = Workflow.objects.get_or_create(
                org_id=ticket.org_id, type=ticket.type, name=f'ACL {ticket.type} {digest}',
                defaults={'comment': 'Generated from ACL reviewers.', 'is_system': True},
            )
            workflow = Workflow.objects.select_for_update().get(pk=workflow.pk)
            if not workflow.active_version_id:
                publish_workflow(workflow, {'nodes': [
                    {'id': 'start', 'type': 'start'},
                    {'id': 'review', 'type': 'approval', 'name': 'Review', 'config': {
                        'approvers': {'type': 'user', 'value': ids}, 'strategy': 'any',
                    }},
                    {'id': 'end', 'type': 'end'},
                ], 'edges': [['start', 'review'], ['review', 'end']]})
                Workflow.objects.filter(pk=workflow.pk).update(enabled=True)
                workflow.refresh_from_db()
    ticket.workflow = workflow
    ticket.origin = TicketOrigin.system
    ticket.save(update_fields=['workflow', 'origin'])
    with tmp_to_org(ticket.org_id):
        return submit_ticket(ticket)


@transaction.atomic
def apply_approved_effect(instance, ticket):
    """Dispatch under the instance lock; each handler uses the frozen context."""
    if not available_users(instance.org_id).filter(pk=instance.applicant_id).exists():
        raise WorkflowConfigurationError('The applicant is no longer eligible for access.')
    plugin = get_ticket_plugin(ticket.type)
    mode = instance.context.get('plugin', {}).get('execution_mode', plugin.execution_mode)
    if mode == 'approval_only':
        return None
    if mode != plugin.execution_mode:
        raise WorkflowConfigurationError('The ticket execution mode changed. Submit a new request.')
    with tmp_to_org(instance.org_id):
        return plugin.on_approved(instance, ticket)


def deliver_event(event_id):
    """Delivery is outside the DB transaction; stale tasks never get action links."""
    from tickets.models import WorkflowEvent
    from tickets.notifications import TicketAppliedToAssigneeMessage, TicketUpdatedToCcUserMessage
    from tickets.utils import send_ticket_processed_mail_to_applicant, send_ticket_updated_mail_to_cc_users
    with tmp_to_root_org():
        event = WorkflowEvent.objects.select_related('instance__ticket', 'task__assignee', 'actor').get(pk=event_id)
        ticket = event.instance.ticket
        with tmp_to_org(ticket.org_id):
            if event.type == 'approval.created':
                task = event.task
                if task.state == 'pending' and task.assignee_id:
                    TicketAppliedToAssigneeMessage(task.assignee, ticket, task_id=task.pk).publish_async()
            elif event.type == 'cc.added':
                # A terminal event already notifies every CC recipient. A CC
                # node immediately before the end must not send twice.
                if ticket.status == 'closed':
                    return
                ids = [recipient['id'] for recipient in event.data.get('recipients', [])]
                users = available_users(ticket.org_id).filter(pk__in=ids).exclude(pk=ticket.applicant_id)
                for user in users:
                    TicketUpdatedToCcUserMessage(user, ticket).publish_async()
            else:
                if ticket.applicant_id:
                    send_ticket_processed_mail_to_applicant(ticket, event.actor or ticket.processor)
                send_ticket_updated_mail_to_cc_users(ticket)


@receiver(workflow_event, dispatch_uid='ticket_workflow_business')
def on_workflow_event(sender, instance, event, **kwargs):
    ticket = instance.ticket
    if event.type == 'workflow.started':
        Ticket.objects.filter(pk=ticket.pk).update(state='pending', status='open')
    if event.type in ('workflow.completed', 'workflow.cancelled', 'workflow.expired', 'workflow.error'):
        if instance.state == 'approved':
            effect = apply_approved_effect(instance, ticket)
        state = {'cancelled': 'closed'}.get(instance.state, instance.state)
        Ticket.objects.filter(pk=ticket.pk).update(state=state, status='closed', date_updated=timezone.now())
        if instance.state == 'approved' and effect is not None:
            from tickets.models import WorkflowEvent
            WorkflowEvent.objects.create(instance=instance, type='action.executed',
                                         data=effect)
    if event.type in ('approval.created', 'cc.added', 'workflow.completed', 'workflow.cancelled', 'workflow.expired', 'workflow.error'):
        transaction.on_commit(lambda: deliver_event(event.pk), robust=True)
