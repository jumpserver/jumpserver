import logging
import uuid
from collections import defaultdict
from types import SimpleNamespace
from uuid import UUID

import django.db.models.deletion
from django.conf import settings
from django.core.exceptions import FieldError, ValidationError
from django.db import migrations, models, transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext

import tickets.plugins.registry


ROOT_ID = '00000000-0000-0000-0000-000000000000'
SYSTEM_ID = '00000000-0000-0000-0000-000000000004'
SYSTEM_ADMIN_ID = '00000000-0000-0000-0000-000000000001'
TYPES = {
    'apply_asset': 'Apply for asset',
    'change_secret': 'Change account password',
    'command_confirm': 'Command confirm',
    'download_replay': 'Download session recording',
    'file_transfer': 'File upload / download',
    'login_asset_confirm': 'Login asset confirm',
    'login_confirm': 'Login confirm',
    'view_secret': 'View account password',
}

logger = logging.getLogger(__name__)


def detach_legacy_foreign_keys(apps, schema_editor):
    legacy = [apps.get_model('tickets', name) for name in (
        'ApplyAssetTicket', 'ApplyLoginTicket', 'ApplyLoginAssetTicket', 'ApplyCommandTicket',
    )]
    asset_ticket = legacy[0]
    legacy.extend(asset_ticket._meta.get_field(name).remote_field.through
                  for name in ('apply_assets', 'apply_nodes'))
    for model in legacy:
        for field in model._meta.local_fields:
            if not isinstance(field, models.ForeignKey) or not field.db_constraint:
                continue
            # Django's deletion collector will no longer know these retained tables.
            detached = field.clone()
            detached.db_constraint = False
            detached.model = model
            detached.set_attributes_from_name(field.name)
            detached.remote_field.model = field.remote_field.model
            schema_editor.alter_field(model, field, detached, strict=True)
            # SQLite rebuilds from model metadata on each successive alteration.
            field.db_constraint = False


def user_snapshot(user):
    return {'id': str(user.pk), 'name': user.name, 'username': user.username} if user else {}


def available_users(apps, db, org_id):
    users = apps.get_model('users', 'User')._base_manager.using(db).filter(
        is_active=True, is_service_account=False,
    ).filter(Q(date_expired__isnull=True) | Q(date_expired__gt=timezone.now()))
    if str(org_id) != ROOT_ID:
        bindings = apps.get_model('rbac', 'RoleBinding')._base_manager.using(db).filter(org_id=org_id)
        users = users.filter(pk__in=bindings.values('user_id'))
    return users


def uuid_list(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or not 1 <= len(values) <= 1000:
        raise ValueError('Approvers require 1 to 1000 IDs.')
    return list(dict.fromkeys(str(UUID(str(value))) for value in values))


def publish_workflow(apps, db, workflow, definition):
    """Publish the linear start/approval/CC/end graphs produced by this migration."""
    items, edges = definition['nodes'], definition['edges']
    if not 2 <= len(items) <= 128 or len(edges) != len(items) - 1:
        raise ValueError('Invalid legacy workflow size.')
    keys = [item['id'] for item in items]
    if len(set(keys)) != len(keys) or items[0]['type'] != 'start' or items[-1]['type'] != 'end':
        raise ValueError('Invalid legacy workflow nodes.')
    if edges != [[a, b] for a, b in zip(keys, keys[1:])]:
        raise ValueError('Invalid legacy workflow edges.')
    normalized = []
    for index, item in enumerate(items):
        kind, config = item['type'], dict(item.get('config', {}))
        if kind == 'approval':
            selector = config.get('approvers', {})
            if selector.get('type') not in ('user', 'role'):
                raise ValueError('Unsupported legacy approver selector.')
            config['approvers'] = {'type': selector['type'], 'value': uuid_list(selector.get('value'))}
            config.update(strategy='any', allow_transfer=False, allow_add_approver=False,
                          timeout=0, timeout_action='expire')
            config.setdefault('exclude_applicant', True)
        elif kind == 'cc':
            ids = uuid_list(config.get('users'))
            valid = {str(pk) for pk in available_users(apps, db, workflow.org_id).filter(pk__in=ids).values_list('pk', flat=True)}
            if valid != set(ids):
                raise ValueError('A legacy CC recipient is missing or unavailable.')
            config = {'users': ids}
        elif not (kind == 'start' and index == 0 or kind == 'end' and index == len(items) - 1):
            raise ValueError('Unsupported legacy workflow node.')
        normalized.append((item, config))
    Version = apps.get_model('tickets', 'WorkflowVersion')
    Node = apps.get_model('tickets', 'WorkflowNode')
    Edge = apps.get_model('tickets', 'WorkflowEdge')
    version = Version._base_manager.using(db).create(workflow_id=workflow.pk, number=1, published_at=timezone.now())
    nodes = {}
    for item, config in normalized:
        nodes[item['id']] = Node._base_manager.using(db).create(
            version_id=version.pk, key=item['id'], name=item.get('name', item['id']),
            type=item['type'], config=config,
        )
    Edge._base_manager.using(db).bulk_create([
        Edge(version_id=version.pk, source_id=nodes[a].pk, target_id=nodes[b].pk)
        for a, b in edges
    ])
    apps.get_model('tickets', 'Workflow')._base_manager.using(db).filter(pk=workflow.pk).update(active_version_id=version.pk)
    return version


def selected_users(apps, db, org_id, selector):
    users = available_users(apps, db, org_id)
    kind = selector.get('type')
    if kind == 'ids':
        ids = uuid_list(selector.get('ids'))
        users = users.filter(pk__in=ids)
        if {str(pk) for pk in users.values_list('pk', flat=True)} != set(ids):
            raise ValueError('A legacy approver is missing or unavailable.')
        return users
    if kind == 'all':
        return users
    if kind != 'attrs' or not isinstance(selector.get('attrs'), list) or not selector['attrs']:
        raise ValueError('Invalid legacy user selector.')
    for attr in selector['attrs']:
        if not isinstance(attr, dict) or not attr.get('name') or 'value' not in attr:
            raise ValueError('Invalid legacy user filter.')
        name, value, match = attr['name'], attr['value'], attr.get('match', 'exact')
        if name in ('system_roles', 'org_roles'):
            ids = uuid_list(value)
            bindings = apps.get_model('rbac', 'RoleBinding')._base_manager.using(db).filter(
                scope='system' if name == 'system_roles' else 'org', role_id__in=ids,
            )
            if name == 'system_roles':
                bindings = bindings.filter(org__isnull=True)
            elif str(org_id) != ROOT_ID:
                bindings = bindings.filter(org_id=org_id)
            if match == 'm2m_all':
                bindings = bindings.values('user_id').annotate(count=Count('role_id', distinct=True)).filter(count=len(ids))
            users = users.filter(pk__in=bindings.values('user_id'))
        elif match in ('m2m', 'm2m_all', 'in'):
            values = value if isinstance(value, list) else [value]
            if match == 'in' and '*' in values:
                continue
            for values in ([[v] for v in values] if match == 'm2m_all' else [values]):
                users = users.filter(**{name + '__in': values})
        elif match == 'not':
            users = users.exclude(**{name: value})
        elif match in ('exact', 'contains', 'startswith', 'endswith', 'gte', 'lte', 'gt', 'lt', 'regex'):
            if match == 'exact' and value == '*':
                continue
            users = users.filter(**{name + '__' + match: value})
        else:
            raise ValueError('Unsupported legacy user filter.')
    return users.distinct()


def convert_flow(apps, db, flow):
    nodes = [{'id': 'start', 'type': 'start'}]
    notes, preserved = [], True
    cc = [str(pk) for pk in flow.cc_users.using(db).values_list('pk', flat=True)]
    if cc:
        nodes.append({'id': 'cc_legacy', 'type': 'cc', 'name': 'CC', 'config': {'users': cc}})
    rules = list(flow.rules.using(db).order_by('level', 'id'))
    if not rules:
        raise ValueError('The legacy flow has no approval rules.')
    for index, rule in enumerate(rules, 1):
        selector = getattr(rule.users, 'value', rule.users) or {}
        attrs = selector.get('attrs', []) if selector.get('type') == 'attrs' else []
        role = attrs[0] if len(attrs) == 1 else {}
        if isinstance(role, dict) and role.get('name') in ('system_roles', 'org_roles') and role.get('match') == 'm2m':
            ids = uuid_list(role.get('value'))
            scope = 'system' if role['name'] == 'system_roles' else 'org'
            roles = apps.get_model('rbac', 'Role')._base_manager.using(db).filter(pk__in=ids, scope=scope)
            if roles.count() != len(ids):
                raise ValueError('A legacy approver role is missing or has a different scope.')
            approvers = {'type': 'role', 'value': ids}
            count = None
        else:
            users = list(selected_users(apps, db, flow.org_id, selector).order_by('id')[:1001])
            if not 1 <= len(users) <= 1000:
                raise ValueError(f'Legacy level {rule.level} has no eligible approvers or exceeds 1000 users.')
            approvers = {'type': 'user', 'value': [str(user.pk) for user in users]}
            count = len(users)
            preserved = preserved and selector.get('type') == 'ids'
        nodes.append({'id': f'approval_{index}', 'type': 'approval', 'name': f'Approval {index}',
                      'config': {'approvers': approvers}})
        notes.append({'level': rule.level, 'legacy_selector': selector, 'resolved_user_count': count})
    nodes.append({'id': 'end', 'type': 'end'})
    return {'nodes': nodes, 'edges': [[a['id'], b['id']] for a, b in zip(nodes, nodes[1:])]}, {
        'rules': notes, 'cc_user_ids': cc, 'requires_review': not preserved,
    }


def import_flow(apps, db, flow):
    Workflow = apps.get_model('tickets', 'Workflow')
    workflows = Workflow._base_manager.using(db)
    if workflows.filter(legacy_flow_id=flow.pk).exists():
        return []
    name = flow.name or gettext(TYPES.get(flow.type, 'General'))
    if workflows.filter(org_id=flow.org_id, type=flow.type, name=name).exists():
        name = f'{name[:89]} ({flow.pk})'
    try:
        definition, notes = convert_flow(apps, db, flow)
        cc = notes['cc_user_ids']
        if cc and available_users(apps, db, flow.org_id).filter(pk__in=cc).count() != len(set(cc)):
            raise ValueError('A legacy CC recipient is missing or unavailable.')
    except (ValueError, TypeError, AttributeError, FieldError) as exc:
        reason = str(exc)[:200]
        workflows.create(org_id=flow.org_id, type=flow.type, name=name, legacy_flow_id=flow.pk,
                         enabled=False, created_by='Legacy workflow import',
                         migration_notes={'requires_review': True, 'error': reason})
        return [reason]
    workflow = workflows.create(
        org_id=flow.org_id, type=flow.type, name=name, legacy_flow_id=flow.pk,
        enabled=not notes['requires_review'], created_by='Legacy workflow import', migration_notes=notes,
    )
    publish_workflow(apps, db, workflow, definition)
    return ['Complex legacy selector requires review.'] if notes['requires_review'] else []


def default_workflows(apps, db):
    Workflow = apps.get_model('tickets', 'Workflow')
    Flow = apps.get_model('tickets', 'TicketFlow')
    Organization = apps.get_model('orgs', 'Organization')
    for kind, label in TYPES.items():
        if not Workflow._base_manager.using(db).filter(type=kind, is_system=False).exists() and not Flow._base_manager.using(db).filter(type=kind).exists():
            yield ROOT_ID, kind, gettext(label)
        else:
            for org_id in Organization._base_manager.using(db).exclude(pk__in=[ROOT_ID, SYSTEM_ID]).values_list('pk', flat=True):
                yield str(org_id), kind, gettext(label)


def create_default(apps, db, org_id, kind, label):
    Workflow = apps.get_model('tickets', 'Workflow')
    Flow = apps.get_model('tickets', 'TicketFlow')
    scopes = [str(org_id), ROOT_ID]
    if (Workflow._base_manager.using(db).filter(org_id__in=scopes, type=kind, is_system=False).exists()
            or Flow._base_manager.using(db).filter(org_id__in=scopes, type=kind).exists()):
        return
    workflow = Workflow._base_manager.using(db).create(org_id=str(org_id), type=kind, name=label, enabled=True, created_by='System')
    publish_workflow(apps, db, workflow, {'nodes': [
        {'id': 'start', 'type': 'start'},
        {'id': 'approval', 'type': 'approval', 'name': 'Approval',
         'config': {'approvers': {'type': 'role', 'value': [SYSTEM_ADMIN_ID]}}},
        {'id': 'end', 'type': 'end'},
    ], 'edges': [['start', 'approval'], ['approval', 'end']]})


def asset_snapshots(apps, db, org_id, ids):
    ids = set(ids)
    if not ids or any(not pk for pk in ids):
        raise ValueError('Requested assets are missing or outside the ticket organization.')
    ids = {str(pk) for pk in ids}
    assets = list(apps.get_model('assets', 'Asset').objects.using(db).filter(
        pk__in=ids, org_id=org_id,
    ).select_related('owner', 'platform').order_by('id'))
    if not ids or len(assets) != len(ids):
        raise ValueError('Requested assets are missing or outside the ticket organization.')
    labels = defaultdict(lambda: defaultdict(list))
    for row in apps.get_model('labels', 'LabeledResource').objects.using(db).filter(
        res_id__in=ids, org_id=org_id, res_type__app_label='assets', res_type__model='asset',
    ).select_related('label').order_by('label__name', 'label__value'):
        labels[row.res_id][row.label.name].append(row.label.value)
    return [{
        'id': str(asset.pk), 'name': asset.name, 'address': asset.address,
        'owner': user_snapshot(asset.owner), 'owner_ids': [str(asset.owner_id)] if asset.owner_id else [],
        'labels': {name: values[0] if len(values) == 1 else values
                   for name, values in labels[str(asset.pk)].items()},
        'platform': {'id': asset.platform_id, 'name': asset.platform.name,
                     'category': asset.platform.category, 'type': asset.platform.type},
    } for asset in assets]


def asset_request_context(apps, db, ticket):
    data = ticket.request_data
    node_ids = data.get('apply_nodes') or []
    nodes = list(apps.get_model('assets', 'Node').objects.using(db).filter(
        pk__in=node_ids, org_id=ticket.org_id,
    ).order_by('id'))
    if len(nodes) != len(set(node_ids)):
        raise ValueError('A requested node was deleted or moved.')
    ids = set(data.get('apply_assets') or [])
    Asset = apps.get_model('assets', 'Asset')
    for node in nodes:
        descendants = Q(nodes__key=node.key) | Q(nodes__key__startswith=f'{node.key}:')
        ids.update(str(pk) for pk in Asset.objects.using(db).filter(
            descendants, org_id=ticket.org_id, nodes__org_id=ticket.org_id,
        ).values_list('pk', flat=True))
    assets = asset_snapshots(apps, db, ticket.org_id, ids)
    selectors = data.get('apply_accounts') or []
    if not isinstance(selectors, list) or not selectors or any(not isinstance(s, str) for s in selectors):
        raise ValueError('Select valid accounts before submitting the request.')
    start = parse_datetime(data['apply_date_start']) if data.get('apply_date_start') else None
    end = parse_datetime(data['apply_date_expired']) if data.get('apply_date_expired') else None
    if not start or not end or end <= start:
        raise ValueError('A valid access period is required.')
    user_ids = data.get('apply_users', [str(ticket.applicant_id)])
    users = list(available_users(apps, db, ticket.org_id).filter(pk__in=user_ids).order_by('id'))
    if not user_ids or len(users) != len(set(user_ids)):
        raise ValueError('An authorized user is missing or outside the organization.')
    accounts = apps.get_model('accounts', 'Account').objects.using(db).filter(
        asset_id__in=ids, org_id=ticket.org_id,
    ).values('id', 'asset_id', 'username', 'secret_type').order_by('asset_id', 'username', 'id')
    if '@ALL' not in selectors:
        accounts = accounts.filter(username__in=selectors)
    accounts = list(accounts)
    grant_selectors = sorted(set([s for s in selectors if s != '@ALL'] + (
        [account['username'] for account in accounts] if '@ALL' in selectors else []
    )))
    if not grant_selectors:
        raise ValueError('No accounts matched the request.')
    snapshots = [{**a, 'id': str(a['id']), 'asset_id': str(a['asset_id'])} for a in accounts]
    known = {a['username'] for a in accounts}
    for selector in dict.fromkeys(selectors):
        if selector == '@ALL' or selector in known:
            continue
        if selector == '@USER':
            snapshots.extend({'selector': selector, 'username': user.username} for user in users)
        else:
            username = '' if selector == '@ANON' else (None if selector.startswith('@') else selector)
            snapshots.append({'selector': selector, 'username': username})
    actions = data.get('apply_actions')
    if type(actions) is not int:
        raise ValueError('Select valid asset actions.')
    return {
        'assets': assets, 'accounts': snapshots,
        'nodes': [{'id': str(node.pk), 'name': node.value} for node in nodes],
        'actions': [name for index, name in enumerate(
            ['connect', 'upload', 'download', 'copy', 'paste', 'delete', 'share']) if actions & (1 << index)],
        'duration': (end - start).total_seconds(),
        'request': {
            'permission_name': data.get('apply_permission_name') or f'Ticket {ticket.pk}',
            'users': [user_snapshot(user) for user in users],
            'is_on_behalf': len(users) != 1 or users[0].pk != ticket.applicant_id,
            'account_selectors': grant_selectors, 'actions': actions,
            'date_start': start.isoformat(), 'date_expired': end.isoformat(),
            'expire_soon_notice_minutes': data.get('apply_expire_soon_notice_minutes'),
        },
    }


def build_context(apps, db, ticket):
    data = ticket.request_data
    if not isinstance(data, dict):
        raise ValueError('Invalid legacy request data.')
    required = {'apply_asset': 'apply_actions', 'login_confirm': 'apply_login_ip',
                'login_asset_confirm': 'apply_login_asset', 'command_confirm': 'apply_run_command'}
    if ticket.type in required and required[ticket.type] not in data:
        raise ValueError('Legacy request data was not copied; inspect the retained child table.')
    if ticket.type == 'apply_asset':
        context = asset_request_context(apps, db, ticket)
    elif ticket.type == 'login_confirm':
        context = {'request': {'ip': data.get('apply_login_ip'), 'city': data.get('apply_login_city'),
                               'datetime': data.get('apply_login_datetime')}}
    elif ticket.type == 'login_asset_confirm':
        connections = (ticket.meta or {}).get('login_asset_connections') or [{
            'asset_id': data.get('apply_login_asset'), 'account': data.get('apply_login_account', ''),
        }]
        ids = {entry['asset_id'] for entry in connections}
        context = {'assets': asset_snapshots(apps, db, ticket.org_id, ids),
                   'accounts': [{'asset_id': entry['asset_id'], 'username': entry['account']} for entry in connections]}
    elif ticket.type == 'command_confirm':
        session_id = data.get('apply_from_session')
        session = apps.get_model('terminal', 'Session').objects.using(db).filter(pk=session_id).first() if session_id else None
        if not session:
            raise ValueError('The command session no longer exists.')
        context = {
            'assets': asset_snapshots(apps, db, ticket.org_id, [session.asset_id]),
            'accounts': [{'username': data.get('apply_run_account', '')}],
            'request': {'command': data.get('apply_run_command', ''), 'session_id': str(session.pk),
                        'acl_id': data.get('apply_from_cmd_filter_acl')},
        }
    elif ticket.type == 'general':
        context = {'request': dict(data)}
    else:
        raise ValueError('Unsupported legacy ticket type.')
    context.setdefault('request', {}).update(type=ticket.type, title=ticket.title)
    context['applicant'] = user_snapshot(ticket.applicant)
    context['plugin'] = {'type': ticket.type}
    for key in ('assets', 'accounts', 'nodes'):
        context.setdefault(key, [])
    return context


def import_ticket(apps, db, ticket):
    """Called inside a per-ticket savepoint; existing imports are left untouched."""
    Ticket = apps.get_model('tickets', 'Ticket')
    Workflow = apps.get_model('tickets', 'Workflow')
    Instance = apps.get_model('tickets', 'WorkflowInstance')
    NodeInstance = apps.get_model('tickets', 'WorkflowNodeInstance')
    Task = apps.get_model('tickets', 'ApprovalTask')
    Event = apps.get_model('tickets', 'WorkflowEvent')
    if Instance.objects.using(db).filter(ticket_id=ticket.pk).exists():
        return []
    steps = list(ticket.ticket_steps.using(db).order_by('level', 'id').prefetch_related('ticket_assignees__assignee'))
    nodes, edges, previous = [{'id': 'start', 'type': 'start'}], [], 'start'
    for step in steps:
        key = f'level_{step.level}'
        ids = [str(task.assignee_id) for task in step.ticket_assignees.all() if task.assignee_id]
        nodes.append({'id': key, 'name': f'Approval {step.level}', 'type': 'approval', 'config': {
            'approvers': {'type': 'user', 'value': ids or ['00000000-0000-0000-0000-000000000000']},
            'strategy': 'any', 'exclude_applicant': False,
        }})
        edges.append([previous, key])
        previous = key
    nodes.append({'id': 'end', 'type': 'end'})
    edges.append([previous, 'end'])
    warnings = []
    try:
        context = build_context(apps, db, ticket)
    except (ValueError, TypeError, KeyError, AttributeError, ValidationError) as exc:
        warnings.append(str(exc)[:200])
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
        if not current or not available_users(apps, db, ticket.org_id).filter(pk__in=ids).exists():
            warnings.append('The current legacy step has no eligible approver.')
        if not ticket.applicant_id:
            warnings.append('The legacy applicant no longer exists.')
        if warnings:
            state = 'error'
    workflow = Workflow.objects.using(db).create(
        name=f'Legacy ticket {ticket.pk}', type=ticket.type, org_id=ticket.org_id,
        enabled=False, is_system=True, created_by='Legacy ticket import',
        migration_notes={'ticket_id': str(ticket.pk), 'warnings': warnings},
    )
    version = publish_workflow(apps, db, workflow, {'nodes': nodes, 'edges': edges})
    instance = Instance.objects.using(db).create(
        ticket=ticket, version=version, applicant_id=ticket.applicant_id, context=context, state=state,
        org_id=ticket.org_id, date_started=ticket.date_created,
        date_finished=None if state == 'running' else ticket.date_updated,
    )
    version_nodes = {node.key: node for node in version.nodes.using(db).all()}
    start = NodeInstance.objects.using(db).create(instance=instance, node=version_nodes['start'],
                                               state='approved', date_finished=ticket.date_created)
    NodeInstance.objects.using(db).filter(pk=start.pk).update(date_created=ticket.date_created)
    for step in steps:
        active = state == 'running' and step.level == ticket.approval_step
        if state == 'running' and step.level > ticket.approval_step:
            continue
        run = NodeInstance.objects.using(db).create(
            instance=instance, node=version_nodes[f'level_{step.level}'], required=1,
            state='running' if active else {'pending': 'skipped', 'closed': 'cancelled'}.get(step.state, step.state),
            date_finished=None if active else step.date_updated,
        )
        NodeInstance.objects.using(db).filter(pk=run.pk).update(date_created=step.date_created)
        for old in step.ticket_assignees.all():
            task_state = old.state if old.state in ('approved', 'rejected') else ('pending' if active else 'cancelled')
            task = Task.objects.using(db).create(
                node_instance=run, assignee_id=old.assignee_id, comment=old.comment,
                assignee_snapshot={**user_snapshot(old.assignee), 'display': old.assignee_display},
                state=task_state, date_finished=step.date_updated if task_state != 'pending' else None,
            )
            Task.objects.using(db).filter(pk=task.pk).update(date_created=old.date_created)
            if task_state in ('approved', 'rejected'):
                event = Event.objects.using(db).create(
                    instance=instance, node_instance=run, task=task, type=f'approval.{task_state}',
                    actor_id=old.assignee_id, actor_snapshot=task.assignee_snapshot, data={'source': 'legacy'},
                )
                Event.objects.using(db).filter(pk=event.pk).update(date_created=step.date_updated)
    if state != 'running':
        NodeInstance.objects.using(db).create(instance=instance, node=version_nodes['end'],
                                            state='approved' if state == 'approved' else 'skipped',
                                            date_finished=ticket.date_updated)
    Event.objects.using(db).create(instance=instance, type='workflow.migrated', data={
        'legacy_state': ticket.state, 'state': state, 'warnings': warnings,
        'effects_replayed': False, 'definition': str(version.pk),
    })
    updates = {'workflow_id': workflow.pk}
    if state == 'cancelled' and ticket.state == 'pending':
        updates['state'] = 'closed'
    if state == 'error' and ticket.status == 'open':
        updates.update(state='error', status='closed', date_updated=timezone.now())
    Ticket.objects.using(db).filter(pk=ticket.pk).update(**updates)
    return warnings


def mark_legacy_system_tickets(apps, schema_editor):
    # Django creates deferred indexes after the data updates in this atomic migration.
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')
    # These types were only created by ACL entrypoints before origin was stored.
    Ticket = apps.get_model('tickets', 'Ticket')
    Ticket.objects.using(schema_editor.connection.alias).filter(
        type__in=['login_confirm', 'login_asset_confirm', 'command_confirm'],
    ).update(origin='system')


def migrate_payloads(apps, schema_editor):
    db = schema_editor.connection.alias
    Ticket = apps.get_model('tickets', 'Ticket')

    def copy(model_name, values):
        Model = apps.get_model('tickets', model_name)
        rows = Model.objects.using(db).all()
        if model_name == 'ApplyAssetTicket':
            rows = rows.prefetch_related('apply_assets', 'apply_nodes')
        def copy_row(row):
            payload = dict(row.request_data or {})
            payload.update(values(row))
            Ticket.objects.using(db).filter(pk=row.pk).update(request_data=payload)

        migrate_rows(rows.iterator(chunk_size=500), copy_row, db, f'payloads:{model_name}')

    copy('ApplyAssetTicket', lambda row: {
        'apply_permission_name': row.apply_permission_name,
        'apply_assets': [str(asset.pk) for asset in row.apply_assets.all()],
        'apply_nodes': [str(node.pk) for node in row.apply_nodes.all()],
        'apply_accounts': row.apply_accounts,
        'apply_actions': row.apply_actions,
        'apply_date_start': row.apply_date_start.isoformat() if row.apply_date_start else None,
        'apply_date_expired': row.apply_date_expired.isoformat() if row.apply_date_expired else None,
        'apply_expire_soon_notice_minutes': row.apply_expire_soon_notice_minutes,
    })
    copy('ApplyLoginTicket', lambda row: {
        'apply_login_ip': row.apply_login_ip,
        'apply_login_city': row.apply_login_city,
        'apply_login_datetime': row.apply_login_datetime.isoformat() if row.apply_login_datetime else None,
    })
    copy('ApplyLoginAssetTicket', lambda row: {
        'apply_login_user': str(row.apply_login_user_id) if row.apply_login_user_id else None,
        'apply_login_asset': str(row.apply_login_asset_id) if row.apply_login_asset_id else None,
        'apply_login_account': row.apply_login_account,
    })
    copy('ApplyCommandTicket', lambda row: {
        'apply_run_user': str(row.apply_run_user_id) if row.apply_run_user_id else None,
        'apply_run_asset': row.apply_run_asset,
        'apply_run_command': row.apply_run_command,
        'apply_run_account': row.apply_run_account,
        'apply_from_session': str(row.apply_from_session_id) if row.apply_from_session_id else None,
        'apply_from_cmd_filter_acl': str(row.apply_from_cmd_filter_acl_id) if row.apply_from_cmd_filter_acl_id else None,
    })


def backfill_beneficiaries(apps, schema_editor):
    db = schema_editor.connection.alias
    Ticket = apps.get_model('tickets', 'Ticket')
    Beneficiary = apps.get_model('tickets', 'TicketBeneficiary')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))

    def insert(rows):
        ids = {str(user_id) for _, user_id in rows}
        valid = {str(pk) for pk in User.objects.using(db).filter(pk__in=ids).values_list('pk', flat=True)}
        Beneficiary.objects.using(db).bulk_create([
            Beneficiary(ticket_id=ticket_id, user_id=user_id)
            for ticket_id, user_id in rows if str(user_id) in valid
        ], ignore_conflicts=True)

    batch = []
    tickets = Ticket.objects.using(db).filter(type='apply_asset').values('id', 'applicant_id', 'request_data')
    for ticket in tickets.iterator(chunk_size=500):
        data = ticket['request_data'] or {}
        if not isinstance(data, dict):
            continue
        users = data.get('apply_users') or [ticket['applicant_id']]
        if not isinstance(users, list):
            continue
        for user_id in users:
            try:
                batch.append((ticket['id'], str(UUID(str(user_id)))))
            except (TypeError, ValueError, AttributeError):
                continue
        if len(batch) >= 500:
            insert(batch)
            batch.clear()
    if batch:
        insert(batch)


def migrate_rows(rows, convert, db, kind):
    failed, warned = 0, 0
    failed_samples, warning_samples = [], []
    for row in rows:
        try:
            # Catch outside the savepoint so one bad record cannot poison the transaction.
            with transaction.atomic(using=db):
                warnings = convert(row) or []
            if warnings:
                warned += 1
                detail = '; '.join(str(w) for w in warnings)
                samples = warning_samples
            else:
                continue
        except Exception as exc:
            failed += 1
            detail = f'{type(exc).__name__}: {exc}'
            samples = failed_samples
        if len(samples) < 5:
            samples.append(f'id={row.pk} org={row.org_id}: {" ".join(detail.split())[:160]}')
    if failed or warned:
        samples = (failed_samples + warning_samples)[:5]
        logger.warning('Ticket upgrade %s: %s failed, %s require review; first %s: %s',
                       kind, failed, warned, len(samples), ' | '.join(samples))


def migrate_approval_workflows(apps, schema_editor):
    db = schema_editor.connection.alias
    flows = apps.get_model('tickets', 'TicketFlow').objects.using(db).order_by('id')
    migrate_rows(flows.iterator(), lambda flow: import_flow(apps, db, flow), db, 'flows')
    defaults = (SimpleNamespace(pk=kind, org_id=org_id, label=label)
                for org_id, kind, label in default_workflows(apps, db))
    migrate_rows(defaults, lambda row: create_default(apps, db, row.org_id, row.pk, row.label), db, 'defaults')


def migrate_legacy_tickets(apps, schema_editor):
    db = schema_editor.connection.alias
    tickets = apps.get_model('tickets', 'Ticket').objects.using(db).filter(
        workflow_instance__isnull=True,
    ).order_by('date_created', 'id')
    migrate_rows(tickets.iterator(), lambda ticket: import_ticket(apps, db, ticket), db, 'instances')


class Migration(migrations.Migration):
    dependencies = [
        ('tickets', '0009_ticketassignee_assignee_display_and_more'),
        ('authentication', '0015_connection_token_ticket'),
        ('assets', '0033_workflow_foundation'),
        ('accounts', '0002_auto_20220616_0021'),
        ('labels', '0001_initial'),
        ('terminal', '0001_initial'),
        ('rbac', '0003_auto_20211130_1037'),
        ('users', '0003_alter_user_date_expired'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('type', models.CharField(choices=[('general', 'General'), ('apply_asset', 'Apply for asset'), ('login_confirm', 'Login confirm'), ('command_confirm', 'Command confirm'), ('login_asset_confirm', 'Login asset confirm')], max_length=64, verbose_name='Type')),
                ('enabled', models.BooleanField(default=False, verbose_name='Enabled')),
                ('legacy_flow_id', models.UUIDField(editable=False, null=True, unique=True)),
                ('migration_notes', models.JSONField(default=dict, editable=False)),
            ],
            options={
                'verbose_name': 'Approval workflow',
                'default_permissions': ('add', 'change', 'view'),
                'ordering': ['name', 'id'],
            },
        ),
        migrations.CreateModel(
            name='WorkflowNode',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('key', models.CharField(max_length=64)),
                ('type', models.CharField(choices=[('start', 'Start'), ('approval', 'Approval'), ('condition', 'Condition'), ('end', 'End')], max_length=16)),
                ('name', models.CharField(blank=True, max_length=128)),
                ('config', models.JSONField(default=dict)),
                ('position_x', models.IntegerField(default=0)),
                ('position_y', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Workflow node',
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='ApprovalTask',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('assignee_snapshot', models.JSONField(default=dict, editable=False)),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('transferred', 'Transferred'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='pending', max_length=16)),
                ('is_added', models.BooleanField(default=False)),
                ('date_finished', models.DateTimeField(null=True)),
                ('assignee', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approval_tasks', to=settings.AUTH_USER_MODEL)),
                ('predecessor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='successors', to='tickets.approvaltask')),
            ],
            options={
                'verbose_name': 'Approval task',
                'ordering': ['date_created', 'id'],
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='WorkflowInstance',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('context', models.JSONField(default=dict, editable=False)),
                ('state', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled'), ('expired', 'Expired'), ('error', 'Error')], default='pending', max_length=16)),
                ('date_started', models.DateTimeField(null=True)),
                ('date_finished', models.DateTimeField(null=True)),
                ('applicant', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('ticket', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='workflow_instance', to='tickets.ticket')),
            ],
            options={
                'verbose_name': 'Workflow instance',
                'ordering': ['-date_created', 'id'],
                'default_permissions': ('view',),
            },
        ),
        migrations.CreateModel(
            name='WorkflowNodeInstance',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('state', models.CharField(choices=[('running', 'Running'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('skipped', 'Skipped'), ('cancelled', 'Cancelled')], default='running', max_length=16)),
                ('required', models.PositiveIntegerField(default=0)),
                ('deadline', models.DateTimeField(db_index=True, null=True)),
                ('date_finished', models.DateTimeField(null=True)),
                ('result', models.JSONField(default=dict)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='node_instances', to='tickets.workflowinstance')),
                ('node', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='instances', to='tickets.workflownode')),
            ],
            options={
                'verbose_name': 'Workflow node instance',
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='WorkflowEvent',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('type', models.CharField(max_length=64)),
                ('actor_snapshot', models.JSONField(default=dict, editable=False)),
                ('data', models.JSONField(default=dict)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('task', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tickets.approvaltask')),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='events', to='tickets.workflowinstance')),
                ('node_instance', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tickets.workflownodeinstance')),
            ],
            options={
                'verbose_name': 'Workflow event',
                'ordering': ['id'],
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='approvaltask',
            name='node_instance',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='tasks', to='tickets.workflownodeinstance'),
        ),
        migrations.CreateModel(
            name='WorkflowVersion',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('number', models.PositiveIntegerField()),
                ('published_at', models.DateTimeField(editable=False, null=True)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='versions', to='tickets.workflow')),
            ],
            options={
                'verbose_name': 'Workflow version',
                'default_permissions': (),
                'ordering': ['-number'],
            },
        ),
        migrations.AddField(
            model_name='workflownode',
            name='version',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nodes', to='tickets.workflowversion'),
        ),
        migrations.AddField(
            model_name='workflowinstance',
            name='version',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='instances', to='tickets.workflowversion'),
        ),
        migrations.CreateModel(
            name='WorkflowEdge',
            fields=[
                ('created_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Created by')),
                ('updated_by', models.CharField(blank=True, max_length=128, null=True, verbose_name='Updated by')),
                ('date_created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Date created')),
                ('date_updated', models.DateTimeField(auto_now=True, verbose_name='Date updated')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comment')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('condition', models.BooleanField(null=True)),
                ('priority', models.PositiveIntegerField(default=0)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing', to='tickets.workflownode')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming', to='tickets.workflownode')),
                ('version', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edges', to='tickets.workflowversion')),
            ],
            options={
                'verbose_name': 'Workflow edge',
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='workflow',
            name='active_version',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='tickets.workflowversion'),
        ),
        migrations.AddIndex(
            model_name='approvaltask',
            index=models.Index(fields=['assignee', 'state'], name='tickets_task_assignee_state'),
        ),
        migrations.AddConstraint(
            model_name='approvaltask',
            constraint=models.UniqueConstraint(fields=('node_instance', 'assignee'), name='tickets_approval_task_user_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflowversion',
            constraint=models.UniqueConstraint(fields=('workflow', 'number'), name='tickets_workflow_version_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflownode',
            constraint=models.UniqueConstraint(fields=('version', 'key'), name='tickets_workflow_node_key_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflowedge',
            constraint=models.UniqueConstraint(fields=('version', 'source', 'target'), name='tickets_workflow_edge_uniq'),
        ),
        migrations.AddConstraint(
            model_name='workflow',
            constraint=models.UniqueConstraint(fields=('org_id', 'type', 'name'), name='tickets_workflow_org_name_uniq'),
        ),
        migrations.AddField(
            model_name='ticket',
            name='workflow',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='tickets', to='tickets.workflow', verbose_name='Workflow'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='state',
            field=models.CharField(choices=[('all', 'All'), ('pending', 'Ticket open'), ('closed', 'Ticket closed'), ('approved', 'Ticket approved'), ('rejected', 'Ticket rejected'), ('expired', 'Expired'), ('error', 'Error')], default='pending', max_length=16, verbose_name='State'),
        ),
        migrations.AlterField(
            model_name='ticketassignee',
            name='state',
            field=models.CharField(choices=[('all', 'All'), ('pending', 'Ticket open'), ('closed', 'Ticket closed'), ('approved', 'Ticket approved'), ('rejected', 'Ticket rejected'), ('expired', 'Expired'), ('error', 'Error')], default='pending', max_length=64),
        ),
        migrations.AddField(
            model_name='workflow', name='is_system',
            field=models.BooleanField(default=False, editable=False),
        ),
        migrations.AlterModelOptions(
            name='workflownodeinstance',
            options={'default_permissions': (), 'ordering': ['date_created', 'id'], 'verbose_name': 'Workflow node instance'},
        ),
        migrations.AddField(
            model_name='ticket',
            name='request_data',
            field=models.JSONField(blank=True, default=dict, verbose_name='Request parameters'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='type',
            field=models.CharField(choices=tickets.plugins.registry.ticket_type_choices, default='general', max_length=64, verbose_name='Type'),
        ),
        migrations.AlterField(
            model_name='workflow',
            name='type',
            field=models.CharField(choices=tickets.plugins.registry.ticket_type_choices, max_length=64, verbose_name='Type'),
        ),
        migrations.AlterField(
            model_name='workflownode', name='type',
            field=models.CharField(choices=[
                ('start', 'Start'), ('approval', 'Approval'), ('condition', 'Condition'),
                ('cc', 'CC'), ('end', 'End'),
            ], max_length=16),
        ),
        migrations.AddField(
            model_name='ticket', name='origin',
            field=models.CharField(
                choices=[('manual', 'Manual request'), ('system', 'System triggered')],
                default='manual', max_length=16, verbose_name='Ticket origin',
            ),
        ),
        migrations.RunPython(mark_legacy_system_tickets, migrations.RunPython.noop),
        migrations.RunPython(migrate_payloads),
        migrations.RunPython(detach_legacy_foreign_keys, migrations.RunPython.noop, atomic=False),
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.DeleteModel(name='ApplyAssetTicket'),
            migrations.DeleteModel(name='ApplyLoginTicket'),
            migrations.DeleteModel(name='ApplyLoginAssetTicket'),
            migrations.DeleteModel(name='ApplyCommandTicket'),
        ]),
        migrations.AlterModelOptions(
            name='workflow',
            options={
                'ordering': ['name', 'id'],
                'verbose_name': 'Approval workflow',
                'default_permissions': ('add', 'change', 'view'),
                'permissions': [('apply_asset_for_others', 'Apply for asset access on behalf of another user')],
            },
        ),
        migrations.CreateModel(
            name='TicketBeneficiary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='beneficiaries', to='tickets.ticket')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='benefiting_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'default_permissions': (), 'verbose_name': 'Ticket beneficiary',
                'unique_together': {('ticket', 'user')},
            },
        ),
        migrations.RunPython(backfill_beneficiaries, migrations.RunPython.noop),
        migrations.CreateModel(
            name='TicketSecretAccess',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('account_id', models.UUIDField()),
                ('user_id', models.UUIDField()),
                ('org_id', models.CharField(max_length=36)),
                ('expires_at', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='secret_accesses', to='tickets.ticket')),
            ],
            options={'default_permissions': ()},
        ),
        migrations.AddConstraint(
            model_name='ticketsecretaccess',
            constraint=models.UniqueConstraint(fields=('ticket', 'account_id'), name='tickets_secret_ticket_account_uniq'),
        ),
        migrations.AddIndex(
            model_name='ticketsecretaccess',
            index=models.Index(fields=['user_id', 'expires_at'], name='tickets_secret_user_expire'),
        ),
        migrations.CreateModel(
            name='TicketTransferExecution',
            fields=[
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('ticket', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, primary_key=True, related_name='transfer_execution', serialize=False, to='tickets.ticket')),
                ('state', models.CharField(db_index=True, default='queued', max_length=16)),
                ('files', models.JSONField(default=list)),
                ('remote_addr', models.GenericIPAddressField(null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_started', models.DateTimeField(null=True)),
                ('date_finished', models.DateTimeField(null=True)),
                ('dispatch_after', models.DateTimeField(null=True)),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.CreateModel(
            name='TicketTransferFile',
            fields=[
                ('org_id', models.CharField(blank=True, db_index=True, default='', max_length=36, verbose_name='Organization')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('size', models.PositiveBigIntegerField(default=0)),
                ('sha256', models.CharField(max_length=64)),
                ('kind', models.CharField(default='upload', max_length=8)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('purged_at', models.DateTimeField(null=True)),
                ('owner', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('ticket', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='transfer_files', to='tickets.ticket')),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.RunPython(migrate_approval_workflows, migrations.RunPython.noop),
        migrations.RunPython(migrate_legacy_tickets, migrations.RunPython.noop),
    ]
