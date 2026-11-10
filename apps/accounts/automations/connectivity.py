"""Persist connectivity outcomes; also used with historical models by migrations."""
from uuid import UUID, NAMESPACE_URL, uuid5

from django.db import connections

from assets.automations.base.account_results import get_execution_account_results

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


def save_connectivity_records(execution, record_model=None, using=None, backfill=False):
    if execution.type not in ('ping', 'verify_account'):
        return 0
    if (execution.snapshot or {}).get('personal_credentials'):
        # Personal credentials have their own owner-scoped audit trail.
        return 0
    if record_model is None:
        from accounts.models import ConnectivityRecord
        record_model = ConnectivityRecord
    using = using or execution._state.db or 'default'
    results = get_execution_account_results(execution, include_unresolved=True)
    records = [
        record_model(
            id=uuid5(NAMESPACE_URL, f"connectivity:{execution.id}:{row['id']}"),
            execution_id=execution.id, org_id=execution.org_id, type=execution.type,
            target=row['id'], asset_id=as_uuid(row['asset_id']),
            asset=row['asset_name'], asset_address=row['asset_address'],
            account_id=as_uuid(row['account_id']), account=row['name'],
            username=row['username'], privileged=row['privileged'],
            status=row['status'], error=row['error'],
            date_start=execution.date_start, date_finished=execution.date_finished,
        ) for row in results['rows']
    ]
    # Explicit org IDs come from the execution, including during cross-org
    # migrations. Never reassign them to the command's current organization.
    queryset = record_model._base_manager.using(using)
    if backfill:
        resolved = set(queryset.filter(
            id__in=[record.id for record in records],
        ).exclude(username='').values_list('id', flat=True))
        records = [record for record in records if record.id not in resolved]
    if not records:
        return 0
    options = {'update_conflicts': True, 'update_fields': RECORD_FIELDS}
    if connections[using].features.supports_update_conflicts_with_target:
        options['unique_fields'] = ['id']
    queryset.bulk_create(records, batch_size=500, **options)
    return len(records)


def backfill_connectivity_records(executions, record_model, using):
    count = 0
    executions = executions.filter(
        type__in=('ping', 'verify_account'), date_finished__isnull=False,
    ).only('id', 'org_id', 'type', 'snapshot', 'result', 'date_start', 'date_finished').order_by('id')
    for execution in executions.iterator(chunk_size=100):
        count += save_connectivity_records(execution, record_model, using, backfill=True)
    return count
