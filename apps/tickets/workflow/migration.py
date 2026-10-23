"""Import legacy records without replaying notifications or access grants."""
from django.db import transaction
from django.utils import timezone

from orgs.utils import tmp_to_org
from tickets.models import (Ticket, Workflow, WorkflowInstance, WorkflowNodeInstance, ApprovalTask, WorkflowEvent)
from .approvers import available_users, user_snapshot
from .business import build_context
from .errors import WorkflowConfigurationError
from .publication import publish_workflow


def legacy_ticket_data(ticket):
    steps = list(ticket.ticket_steps.order_by('level', 'id').prefetch_related('ticket_assignees__assignee'))
    nodes, edges, previous = [{'id': 'start', 'type': 'start'}], [], 'start'
    for step in steps:
        key = f'level_{step.level}'
        ids = [str(task.assignee_id) for task in step.ticket_assignees.all() if task.assignee_id]
        nodes.append({'id': key, 'name': f'Approval {step.level}', 'type': 'approval', 'config': {
            # Preserve the original participant set, including old self-approval policy.
            'approvers': {'type': 'user', 'value': ids or ['00000000-0000-0000-0000-000000000000']},
            'strategy': 'any', 'exclude_applicant': False,
        }})
        edges.append([previous, key])
        previous = key
    nodes.append({'id': 'end', 'type': 'end'})
    edges.append([previous, 'end'])
    warnings = []
    try:
        context = build_context(ticket)
    except (WorkflowConfigurationError, AttributeError) as exc:
        warnings.append(str(exc))
        context = {'applicant': user_snapshot(ticket.applicant), 'request': {'type': ticket.type, 'title': ticket.title}}
    context['legacy'] = {
        'rel_snapshot': ticket.rel_snapshot, 'approval_step': ticket.approval_step,
        'state': ticket.state, 'status': ticket.status, 'snapshot_at': timezone.now().isoformat(),
        'note': 'Business context was captured at migration, not at original submission.',
    }
    state = {'pending': 'running', 'closed': 'cancelled'}.get(ticket.state, ticket.state)
    if state == 'running' and ticket.status == 'closed':
        state = 'cancelled'
    if state == 'running':
        current = next((step for step in steps if step.level == ticket.approval_step), None)
        ids = [task.assignee_id for task in current.ticket_assignees.all()] if current else []
        if not current or not available_users(ticket.org_id).filter(pk__in=ids).exists():
            warnings.append('The current legacy step has no eligible approver.')
        if warnings or not ticket.applicant_id:
            state = 'error'
    return steps, {'nodes': nodes, 'edges': edges}, context, state, warnings


@transaction.atomic
def import_ticket(ticket_id, apply=False):
    ticket = Ticket.objects.select_for_update().get(pk=ticket_id)
    if WorkflowInstance.objects.filter(ticket=ticket).exists():
        return 'SKIP', []
    steps, definition, context, state, warnings = legacy_ticket_data(ticket)
    if not apply:
        return f'WOULD IMPORT ({state})', warnings
    with tmp_to_org(ticket.org_id):
        workflow = Workflow.objects.create(
            name=f'Legacy ticket {ticket.pk}', type=ticket.type, org_id=ticket.org_id, enabled=False,
            is_system=True,
            created_by='Legacy ticket import', migration_notes={'ticket_id': str(ticket.pk), 'warnings': warnings},
        )
        version = publish_workflow(workflow, definition, expected_version=0)
        instance = WorkflowInstance.objects.create(
            ticket=ticket, version=version, applicant=ticket.applicant, context=context, state=state,
            org_id=ticket.org_id,
            date_started=ticket.date_created, date_finished=None if state == 'running' else ticket.date_updated,
        )
        start = WorkflowNodeInstance.objects.create(instance=instance, node=version.nodes.get(key='start'),
                                                   state='approved', date_finished=ticket.date_created)
        WorkflowNodeInstance.objects.filter(pk=start.pk).update(date_created=ticket.date_created)
        for step in steps:
            active = state == 'running' and step.level == ticket.approval_step
            if state == 'running' and step.level > ticket.approval_step:
                # Future nodes resolve their frozen participant set when entered.
                continue
            run_state = 'running' if active else {'pending': 'skipped', 'closed': 'cancelled'}.get(step.state, step.state)
            run = WorkflowNodeInstance.objects.create(
                instance=instance, node=version.nodes.get(key=f'level_{step.level}'), required=1,
                state=run_state, date_finished=None if active else step.date_updated,
            )
            WorkflowNodeInstance.objects.filter(pk=run.pk).update(date_created=step.date_created)
            for old in step.ticket_assignees.all():
                task_state = old.state if old.state in ('approved', 'rejected') else ('pending' if active else 'cancelled')
                task = ApprovalTask.objects.create(
                    node_instance=run, assignee=old.assignee, assignee_snapshot={
                        **user_snapshot(old.assignee), 'name': old.assignee_display,
                    }, state=task_state, date_finished=step.date_updated if task_state != 'pending' else None,
                )
                ApprovalTask.objects.filter(pk=task.pk).update(date_created=old.date_created)
                if task_state in ('approved', 'rejected'):
                    event = WorkflowEvent.objects.create(
                        instance=instance, node_instance=run, task=task, type=f'approval.{task_state}',
                        actor=old.assignee, actor_snapshot=task.assignee_snapshot, data={'source': 'legacy'},
                    )
                    WorkflowEvent.objects.filter(pk=event.pk).update(date_created=step.date_updated)
        if state != 'running':
            WorkflowNodeInstance.objects.create(instance=instance, node=version.nodes.get(key='end'),
                                               state='approved' if state == 'approved' else 'skipped',
                                               date_finished=ticket.date_updated)
        WorkflowEvent.objects.create(instance=instance, type='workflow.migrated', data={
            'legacy_state': ticket.state, 'state': state, 'warnings': warnings,
            'effects_replayed': False, 'definition': str(version.pk),
        })
        updates = {'workflow': workflow}
        if state == 'error' and ticket.status == 'open':
            updates.update(state='error', status='closed', date_updated=timezone.now())
        Ticket.objects.filter(pk=ticket.pk).update(**updates)
    return f'IMPORTED ({state})', warnings
