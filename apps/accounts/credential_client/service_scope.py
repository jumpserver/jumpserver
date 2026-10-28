"""Account storage and service selectors within the v1 Agent sync protocol."""
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from accounts.models import ApplicationCredential


def stored_credential_available(account):
    """Inspect local presence metadata without fetching a remote Vault secret."""
    try:
        source = account.get_source_template() if account.follows_template else account
    except ValidationError:
        return False
    # A Vault marker also counts as present. A later Vault outage remains a
    # fetch failure; it must not be represented as an empty password.
    return source._secret is not None


def service_metadata(manager, scope, known, delivered, now):
    application = manager.application
    application.assert_account_limit()
    accounts = {str(account.id): account for account in application.get_accounts().order_by('id')}
    switching = set(scope.get('switch_account_ids', []))
    requested = set(scope['account_ids'])
    if scope.get('all_authorized'):
        requested.update(accounts)
    # An existing association that is ambiguous, unbound or no longer authorized
    # must fail the service, rather than silently pinning it to its declared A.
    rotations = list(ApplicationCredential.objects.filter(
        mode='alternating_rotation', is_active=True,
    ).filter(Q(account_id__in=set(accounts) | switching) | Q(alternate_account_id__in=set(accounts) | switching))
        .select_related('active_account').prefetch_related('applications').order_by('key'))
    selected = {}
    unavailable = []
    for account_id in sorted(switching):
        matches = [policy for policy in rotations
                   if account_id in (str(policy.account_id), str(policy.alternate_account_id))]
        if not matches:
            if account_id in accounts:
                requested.add(account_id)
            else:
                unavailable.append(account_id)
            continue
        if len(matches) != 1:
            unavailable.append(account_id)
            continue
        policy = matches[0]
        if (str(policy.account_id) not in accounts or str(policy.alternate_account_id) not in accounts
                or not any(app.id == application.id for app in policy.applications.all())
                or str(policy.active_account_id) not in accounts):
            unavailable.append(account_id)
            continue
        selected[policy.key] = policy

    blocked = {str(account_id) for policy in rotations if policy.status != 'idle'
               for account_id in (policy.account_id, policy.alternate_account_id)
               if account_id != policy.active_account_id}
    subscriptions = list(ApplicationCredential.objects.filter(
        applications=application, mode='subscription', is_active=True,
    ).prefetch_related('subscription_accounts').order_by('key'))
    covered = {policy: (set(accounts) if policy.subscription_all_authorized else
                       {str(account.id) for account in policy.subscription_accounts.all()})
               for policy in subscriptions}
    metadata, reports = [], {}
    from .event_results import snapshot_result_event
    for account_id in sorted(requested & accounts.keys()):
        account = accounts[account_id]
        key = f'account:{account_id}'
        item = {
            'key': key, 'revision': account.version, 'account_id': account_id,
            'account_revision': account.version,
            'available': account_id not in blocked and stored_credential_available(account),
            'changed': known.get(key) != account.version,
        }
        policies = [policy for policy in subscriptions if account_id in covered[policy]]
        if item['available'] and policies:
            item['event_id'] = snapshot_result_event(manager.client, policies[0], account, account.version)
            for policy in policies:
                reports.setdefault(policy, []).append((account.version, known.get(key), delivered.get(key)))
        metadata.append(item)
    for key, policy in sorted(selected.items()):
        account = accounts[str(policy.active_account_id)]
        item = {
            'key': key, 'revision': policy.current_revision, 'account_id': str(account.id),
            'account_revision': account.version, 'available': stored_credential_available(account),
            'changed': known.get(key) != policy.current_revision,
            'account_switch': policy.account_switch,
        }
        if item['available']:
            item['event_id'] = snapshot_result_event(manager.client, policy, account, policy.current_revision)
        metadata.append(item)
    manager._record_subscription_progress(reports, now)
    desired = {'credential_keys': sorted(item['key'] for item in metadata),
               'confirmation_keys': sorted(selected)}
    return desired, metadata, unavailable
