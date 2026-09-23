"""Server-side context builders. Never include account secrets in a snapshot."""
from collections import defaultdict

from assets.models import Asset
from accounts.models import Account
from accounts.const import AliasAccount
from orgs.utils import tmp_to_org
from .approvers import user_snapshot
from .errors import WorkflowConfigurationError


def snapshot_assets(assets, org_id):
    """Freeze ownership, labels and platform for the requested, concrete assets.

    Business adapters must expand node selections before calling this helper.
    The engine never looks these values up again during branch/owner resolution.
    """
    ids = {str(asset.pk) for asset in assets}
    with tmp_to_org(org_id):
        assets = list(Asset.objects.filter(pk__in=ids, org_id=org_id).select_related('owner', 'platform'))
        if len(assets) != len(ids):
            raise WorkflowConfigurationError('Requested assets are missing or outside the ticket organization.')
        result = []
        for asset in sorted(assets, key=lambda item: str(item.pk)):
            labels = defaultdict(list)
            for label in asset.get_labels().order_by('name', 'value'):
                labels[label.name].append(label.value)
            result.append({
                'id': str(asset.pk), 'name': asset.name, 'address': asset.address,
                'owner': user_snapshot(asset.owner),
                'owner_ids': [str(asset.owner_id)] if asset.owner_id else [],
                'labels': {name: values[0] if len(values) == 1 else values for name, values in labels.items()},
                'platform': {'id': asset.platform_id, 'name': asset.platform.name,
                             'category': asset.platform.category, 'type': asset.platform.type},
            })
    return result


def snapshot_accounts(selectors, assets, applicant, org_id):
    """Expand @ALL before evaluating username conditions or granting access.

    Manual/unspecified usernames are deliberately null: policies that need a
    concrete username fail closed instead of treating an unknown account as safe.
    No credential-bearing field is loaded from the account table.
    """
    selectors = list(dict.fromkeys(selectors))
    with tmp_to_org(org_id):
        accounts = Account.objects.filter(asset__in=assets).values('id', 'asset_id', 'username', 'secret_type')
        if AliasAccount.ALL not in selectors:
            accounts = accounts.filter(username__in=selectors)
        accounts = list(accounts.order_by('asset_id', 'username', 'id'))
    grant_selectors = [value for value in selectors if value != AliasAccount.ALL]
    if AliasAccount.ALL in selectors:
        grant_selectors.extend(account['username'] for account in accounts)
    grant_selectors = sorted(set(grant_selectors))
    if not grant_selectors:
        raise WorkflowConfigurationError('No accounts matched the request. Select explicit accounts.')
    result = [{**account, 'id': str(account['id']), 'asset_id': str(account['asset_id'])} for account in accounts]
    known_names = {account['username'] for account in accounts}
    for selector in selectors:
        if selector == AliasAccount.ALL or selector in known_names:
            continue
        username = {AliasAccount.USER: applicant.username, AliasAccount.ANON: ''}.get(selector)
        if not selector.startswith('@'):
            username = selector
        result.append({'selector': selector, 'username': username})
    return result, grant_selectors
