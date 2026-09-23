"""Ticket adapters: trusted input snapshots, atomic effects and notifications."""
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from assets.models import Asset
from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.models import Ticket, Workflow
from .approvers import available_users, user_snapshot
from .context import snapshot_assets, snapshot_accounts
from .errors import WorkflowConfigurationError
from .signals import workflow_event


def build_context(ticket):
    applicant = user_snapshot(ticket.applicant)
    applicant['manager_id'] = str(ticket.applicant.manager_id) if ticket.applicant.manager_id else None
    context = {'applicant': applicant, 'request': {'type': ticket.type, 'title': ticket.title},
               'assets': [], 'accounts': [], 'nodes': []}
    assets = []
    with tmp_to_org(ticket.org_id):
        if ticket.type == 'apply_asset':
            nodes = list(ticket.apply_nodes.all())
            ids = set(ticket.apply_assets.values_list('pk', flat=True))
            for node in nodes:
                if node.org_id != ticket.org_id:
                    raise WorkflowConfigurationError('A requested node belongs to another organization.')
                ids.update(node.get_all_assets().values_list('pk', flat=True))
            assets = list(Asset.objects.filter(pk__in=ids, org_id=ticket.org_id))
            if len(assets) != len(ids) or not assets or not ticket.apply_accounts:
                raise WorkflowConfigurationError('Select existing assets and accounts before submitting the request.')
            if not ticket.apply_date_start or not ticket.apply_date_expired or ticket.apply_date_expired <= ticket.apply_date_start:
                raise WorkflowConfigurationError('A valid access period is required.')
            context['nodes'] = [{'id': str(n.pk), 'name': n.value} for n in nodes]
            context['accounts'], grant_accounts = snapshot_accounts(ticket.apply_accounts, assets, ticket.applicant, ticket.org_id)
            from perms.const import ActionChoices
            context['actions'] = [action.name for action in ActionChoices if action.value & ticket.apply_actions]
            context['duration'] = (ticket.apply_date_expired - ticket.apply_date_start).total_seconds()
            context['request'].update({
                'permission_name': ticket.apply_permission_name,
                'account_selectors': grant_accounts,
                'actions': ticket.apply_actions,
                'date_start': ticket.apply_date_start.isoformat(),
                'date_expired': ticket.apply_date_expired.isoformat(),
                'expire_soon_notice_minutes': ticket.apply_expire_soon_notice_minutes,
            })
        elif ticket.type == 'login_asset_confirm':
            if not ticket.apply_login_asset_id:
                raise WorkflowConfigurationError('The requested asset no longer exists.')
            assets = [ticket.apply_login_asset]
            context['accounts'] = [{'username': ticket.apply_login_account}]
        elif ticket.type == 'command_confirm':
            session = ticket.apply_from_session
            asset = Asset.objects.filter(pk=session.asset_id, org_id=ticket.org_id).first() if session else None
            if not asset:
                raise WorkflowConfigurationError('The command session asset no longer exists.')
            assets = [asset]
            context['accounts'] = [{'username': ticket.apply_run_account}]
            context['request'].update(command=ticket.apply_run_command, session_id=str(session.pk),
                                      acl_id=str(ticket.apply_from_cmd_filter_acl_id))
        elif ticket.type == 'login_confirm':
            context['request'].update(ip=str(ticket.apply_login_ip), city=str(ticket.apply_login_city),
                                      datetime=str(ticket.apply_login_datetime))
        context['assets'] = snapshot_assets(assets, ticket.org_id)
    return context


@transaction.atomic
def submit_ticket(ticket):
    from .engine import WorkflowEngine
    if not ticket.workflow_id:
        raise WorkflowConfigurationError('Select a published workflow.')
    if not ticket.applicant_id or not available_users(ticket.org_id).filter(pk=ticket.applicant_id).exists():
        raise WorkflowConfigurationError('The applicant must be an active organization member.')
    ticket.set_serial_num()
    cc_users = ticket.workflow.cc_users.filter(pk__in=available_users(ticket.org_id).values('pk'))
    ticket.cc_users.set(cc_users)
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
    ticket.save(update_fields=['workflow'])
    with tmp_to_org(ticket.org_id):
        return submit_ticket(ticket)


@transaction.atomic
def apply_approved_effect(instance, ticket):
    """Run once under the instance lock, using exclusively frozen request data."""
    if not available_users(instance.org_id).filter(pk=instance.applicant_id).exists():
        raise WorkflowConfigurationError('The applicant is no longer eligible for access.')
    if ticket.type in ('login_asset_confirm', 'command_confirm'):
        ids = [asset['id'] for asset in instance.context['assets']]
        with tmp_to_org(instance.org_id):
            if Asset.objects.filter(pk__in=ids, org_id=instance.org_id).count() != len(ids):
                raise WorkflowConfigurationError('The requested asset was deleted or moved.')
    if ticket.type == 'apply_asset':
        from perms.models import AssetPermission
        from perms.utils.expire_soon_notice import sync_expire_soon_notice
        data = instance.context
        requested = data['request']
        if '@USER' in requested['account_selectors'] and instance.applicant.username != data['applicant']['username']:
            raise WorkflowConfigurationError('The dynamic account username changed. Submit a new request.')
        ids = [asset['id'] for asset in data['assets']]
        with tmp_to_org(instance.org_id):
            assets = Asset.objects.filter(pk__in=ids, org_id=instance.org_id)
            if assets.count() != len(ids):
                raise WorkflowConfigurationError('A requested asset was deleted or moved. Submit a new request.')
            if AssetPermission.objects.filter(pk=ticket.pk).exists():
                return
            attrs = {
                'id': ticket.pk, 'from_ticket': True, 'name': requested['permission_name'],
                'accounts': requested['account_selectors'], 'actions': requested['actions'],
                'date_start': parse_datetime(requested['date_start']),
                'date_expired': parse_datetime(requested['date_expired']),
                'expire_soon_notice_minutes': requested['expire_soon_notice_minutes'],
                'comment': f'Ticket {ticket.serial_num}: {ticket.title}',
                'created_by': requested['permission_name'],
            }
            if attrs['date_expired'] <= timezone.now():
                raise WorkflowConfigurationError('The requested access period has already expired.')
            sync_expire_soon_notice(None, attrs, allow_past=True, disable_if_past=True)
            permission = AssetPermission.objects.create(**attrs)
            # Never grant a live node selection: its membership can grow after approval.
            permission.assets.set(assets)
            permission.users.add(instance.applicant)
    elif ticket.type == 'login_asset_confirm':
        ticket.spec_ticket.activate_connection_token_if_need()


def deliver_event(event_id):
    """Delivery is outside the DB transaction; stale tasks never get action links."""
    from tickets.models import WorkflowEvent
    from tickets.notifications import TicketAppliedToAssigneeMessage
    from tickets.utils import send_ticket_processed_mail_to_applicant, send_ticket_updated_mail_to_cc_users
    with tmp_to_root_org():
        event = WorkflowEvent.objects.select_related('instance__ticket', 'task__assignee', 'actor').get(pk=event_id)
        ticket = event.instance.ticket.spec_ticket
        with tmp_to_org(ticket.org_id):
            if event.type == 'approval.created':
                task = event.task
                if task.state == 'pending' and task.assignee_id:
                    TicketAppliedToAssigneeMessage(task.assignee, ticket, task_id=task.pk).publish_async()
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
            apply_approved_effect(instance, ticket)
        state = {'cancelled': 'closed'}.get(instance.state, instance.state)
        Ticket.objects.filter(pk=ticket.pk).update(state=state, status='closed', date_updated=timezone.now())
        if instance.state == 'approved' and ticket.type in ('apply_asset', 'login_asset_confirm'):
            from tickets.models import WorkflowEvent
            WorkflowEvent.objects.create(instance=instance, type='action.executed',
                                         data={'action': ticket.type, 'ticket': str(ticket.pk)})
    if event.type in ('approval.created', 'workflow.completed', 'workflow.cancelled', 'workflow.expired', 'workflow.error'):
        transaction.on_commit(lambda: deliver_event(event.pk), robust=True)
