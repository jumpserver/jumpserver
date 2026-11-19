"""Persist connectivity records from the current execution snapshot."""
from uuid import UUID, NAMESPACE_URL, uuid5

from django.db import connections

from assets.automations.base.account_results import execution_account_results

RECORD_FIELDS = (
    'org_id', 'type', 'target', 'asset_id', 'asset', 'asset_address',
    'account_id', 'account', 'username', 'privileged', 'status', 'error',
    'date_start', 'date_finished',
)


def as_uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def save_connectivity_records(execution):
    if execution.type not in ('ping', 'verify_account'):
        return 0
    if (execution.snapshot or {}).get('personal_credentials'):
        # Personal credentials have their own owner-scoped audit trail.
        return 0
    from accounts.models import ConnectivityRecord

    using = execution._state.db or 'default'
    results = execution_account_results(execution.result)
    records = [
        ConnectivityRecord(
            id=uuid5(NAMESPACE_URL, f"connectivity:{execution.id}:{row['id']}"),
            execution_id=execution.id, org_id=execution.org_id, type=execution.type,
            target=row['id'], asset_id=as_uuid(row['asset_id']),
            asset=row['asset_name'], asset_address=row['asset_address'],
            account_id=as_uuid(row['account_id']), account=row['name'],
            username=row['username'], privileged=row['privileged'],
            status=row['status'], error=row['error'],
            date_start=execution.date_start, date_finished=execution.date_finished,
        ) for row in results
    ]
    # Preserve the execution's organization when writing its records.
    queryset = ConnectivityRecord._base_manager.using(using)
    if not records:
        return 0
    options = {'update_conflicts': True, 'update_fields': RECORD_FIELDS}
    if connections[using].features.supports_update_conflicts_with_target:
        options['unique_fields'] = ['id']
    queryset.bulk_create(records, batch_size=500, **options)
    return len(records)
