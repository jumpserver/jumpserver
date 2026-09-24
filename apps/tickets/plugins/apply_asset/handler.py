from django.utils import timezone
from django.utils.dateparse import parse_datetime

from assets.models import Asset, Node
from orgs.utils import tmp_to_org
from tickets.workflow.approvers import available_users, user_snapshot
from tickets.workflow.context import snapshot_assets, snapshot_accounts
from tickets.workflow.errors import WorkflowConfigurationError


def requested_users(ticket):
    ids = ticket.request_data.get('apply_users', [str(ticket.applicant_id)])
    users = list(available_users(ticket.org_id).filter(pk__in=ids).order_by('id'))
    if not ids or len(users) != len(set(ids)):
        raise WorkflowConfigurationError('Select active organization members as authorized users.')
    return users


def build_context(ticket):
    data = ticket.request_data
    context = {'request': {}}
    node_ids = data.get('apply_nodes') or []
    asset_ids = data.get('apply_assets') or []
    nodes = list(Node.objects.filter(pk__in=node_ids, org_id=ticket.org_id))
    if len(nodes) != len(set(node_ids)):
        raise WorkflowConfigurationError('A requested node was deleted or moved.')
    ids = set(asset_ids)
    for node in nodes:
        if node.org_id != ticket.org_id:
            raise WorkflowConfigurationError('A requested node belongs to another organization.')
        ids.update(str(pk) for pk in node.get_all_assets().values_list('pk', flat=True))
    assets = list(Asset.objects.filter(pk__in=ids, org_id=ticket.org_id))
    accounts = data.get('apply_accounts') or []
    date_start = parse_datetime(data['apply_date_start']) if data.get('apply_date_start') else None
    date_expired = parse_datetime(data['apply_date_expired']) if data.get('apply_date_expired') else None
    if len(assets) != len(ids) or not assets or not accounts:
        raise WorkflowConfigurationError('Select existing assets and accounts before submitting the request.')
    if not date_start or not date_expired or date_expired <= date_start:
        raise WorkflowConfigurationError('A valid access period is required.')
    context['nodes'] = [{'id': str(n.pk), 'name': n.value} for n in nodes]
    users = requested_users(ticket)
    context['accounts'] = []
    account_users = users if '@USER' in accounts else users[:1]
    seen = set()
    for user in account_users:
        account_snapshots, grant_accounts = snapshot_accounts(accounts, assets, user, ticket.org_id)
        for account in account_snapshots:
            key = tuple(sorted(account.items()))
            if key not in seen:
                seen.add(key)
                context['accounts'].append(account)
    from perms.const import ActionChoices
    actions = data.get('apply_actions')
    if not isinstance(actions, int):
        raise WorkflowConfigurationError('Select valid asset actions.')
    context['actions'] = [action.name for action in ActionChoices if action.value & actions]
    context['duration'] = (date_expired - date_start).total_seconds()
    context['request'].update({
        'permission_name': data.get('apply_permission_name') or f'Ticket {ticket.pk}',
        'users': [user_snapshot(user) for user in users],
        'account_selectors': grant_accounts,
        'actions': actions,
        'date_start': date_start.isoformat(),
        'date_expired': date_expired.isoformat(),
        'expire_soon_notice_minutes': data.get('apply_expire_soon_notice_minutes'),
    })
    context['assets'] = snapshot_assets(assets, ticket.org_id)
    return context


def on_approved(instance, ticket):
    from perms.models import AssetPermission
    from perms.utils.expire_soon_notice import sync_expire_soon_notice
    data = instance.context
    requested = data['request']
    snapshots = requested.get('users', [data['applicant']])
    users = list(available_users(instance.org_id).filter(pk__in=[user['id'] for user in snapshots]))
    if len(users) != len(snapshots):
        raise WorkflowConfigurationError('An authorized user is no longer an active organization member.')
    if '@USER' in requested['account_selectors']:
        names = {user['id']: user['username'] for user in snapshots}
        if any(user.username != names[str(user.pk)] for user in users):
            raise WorkflowConfigurationError('A dynamic account username changed. Submit a new request.')
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
        permission.users.set(users)
    return {'action': ticket.type, 'ticket': str(ticket.pk)}
