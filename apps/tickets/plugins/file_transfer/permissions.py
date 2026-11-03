"""Transfer tickets add actions to existing access, never establish access."""
from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone

from perms.const import ActionChoices
from perms.models import AssetPermission
from perms.utils.asset_perm import PermAssetDetailUtil
from perms.utils.permission import AssetPermissionUtil
from tickets.models import Ticket
from tickets.workflow.approvers import available_users

TRANSFER_PROTOCOLS = {'ssh', 'sftp', 'rdp', 'winrm'}


def executable_protocols(asset):
    if not asset or asset.category != 'host':
        return set()
    return {'linux': {'ssh', 'sftp'}, 'windows': {'winrm'}}.get(asset.type, set())


def base_access(user, asset, permissions=None):
    if not asset.is_active or not available_users(asset.org_id).filter(pk=user.pk).exists():
        return {}
    if permissions is None:
        permissions = list(AssetPermissionUtil().get_permissions_for_user_asset(user, asset))
    result = {}
    for protocol in set(asset.protocols.values_list('name', flat=True)) & TRANSFER_PROTOCOLS:
        matching = [p for p in permissions if protocol in p.protocols or 'all' in p.protocols]
        accounts = PermAssetDetailUtil.get_permed_accounts_from_perms(matching, user, asset)
        for account in accounts:
            if (account.asset_id != asset.pk or not account.is_active or
                    not ActionChoices.contains(account.actions, ActionChoices.connect)):
                continue
            item = result.setdefault(str(account.pk), {'username': account.username, 'protocols': []})
            item['protocols'].append(protocol)
    for item in result.values():
        item['protocols'].sort()
    return result


def is_executable(instance):
    return bool(instance and instance.context.get('file_transfer_version') == 1)


def approved_grants(user, asset, ticket_id=None):
    tickets = Ticket.objects.filter(
        type='file_transfer', org_id=asset.org_id, applicant=user,
        state='approved', status='closed', workflow_instance__state='approved',
    )
    grants = AssetPermission.objects.valid().filter(
        pk__in=tickets.values('pk'), from_ticket=True, org_id=asset.org_id, assets=asset, users=user,
    )
    if ticket_id is not None:
        grants = grants.filter(pk=ticket_id)
    grants = {grant.pk: grant for grant in grants}
    if not grants:
        return []
    tickets = tickets.filter(pk__in=grants).select_related('workflow_instance')
    result = []
    for ticket in tickets:
        instance = ticket.workflow_instance
        if not is_executable(instance) or not instance.date_finished:
            continue
        context = instance.context
        grant = grants[ticket.pk]
        if (instance.applicant_id != user.pk or str(instance.org_id) != str(asset.org_id) or
                context['request']['asset'] != str(asset.pk)):
            continue
        expires = min(grant.date_expired, instance.date_finished + timedelta(seconds=context['duration']))
        if expires > timezone.now():
            result.append((grant, context, expires))
    return result


def effective_transfer_actions(user, asset, permissions, grants, protocol=None):
    access = base_access(user, asset, permissions)
    actions = {}
    for grant, context, _expires in grants:
        direction = context['request']['direction']
        bit = {'upload': ActionChoices.upload, 'download': ActionChoices.download}[direction]
        bit &= grant.actions
        for snapshot in context['accounts']:
            account_id = snapshot['id']
            current = access.get(account_id)
            if (not current or current['username'] != snapshot['username'] or
                    snapshot['username'] not in grant.accounts):
                continue
            protocols = (set(current['protocols']) & set(context['transfer_protocols'].get(account_id, [])) &
                         set(grant.protocols))
            if not protocols or (protocol is not None and protocol not in protocols):
                continue
            # Reuse exclusion handling, including @ALL and dynamic account aliases.
            extra = SimpleNamespace(accounts=[snapshot['username']], actions=bit, date_expired=grant.date_expired)
            combined, _ = PermAssetDetailUtil.parse_alias_action_date_expire([*permissions, extra], asset)
            allowed = combined.get(snapshot['username'], 0) & bit
            actions[account_id] = actions.get(account_id, 0) | allowed
    return actions


def add_transfer_actions(user, asset, accounts, permissions, protocol=None):
    grants = approved_grants(user, asset)
    if grants:
        actions = effective_transfer_actions(user, asset, permissions, grants, protocol)
        for account in accounts:
            account.actions |= actions.get(str(account.pk), 0)
    return accounts
