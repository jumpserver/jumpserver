"""Policy-owned event cycles and their frozen, per-event recipient receipts."""
from collections import defaultdict

from django.db.models import Case, CharField, Count, Exists, IntegerField, Max, Min, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Cast, Coalesce
from rest_framework.exceptions import NotFound

from accounts.const import ApplicationEvent, AuditEvent
from accounts.models import Account, ApplicationAudit, CredentialClientInstance, CredentialRotationEvent
from common.utils import get_log_keep_day


def policy_events(credential):
    source_ids = ApplicationAudit.objects.filter(
        credential_id=credential.id, org_id=credential.org_id,
    ).values('id')
    # Application-wide scope events belong to the application's history,
    # not to the timeline of events emitted by this particular policy.
    return CredentialRotationEvent.objects.filter(
        Q(rotation__credential=credential) | Q(source_event_id__in=source_ids),
        org_id=credential.org_id,
    ).annotate(cycle_key=Coalesce('cycle_id', 'rotation_id', 'source_event_id'))


def _ordered(events):
    if events and events[0].rotation_id:
        return sorted(events, key=lambda event: event.sequence)
    return sorted(events, key=lambda event: (event.published_at, event.id))


def _context(events, org_id):
    audits = {
        audit.id: audit for audit in ApplicationAudit.objects.filter(
            id__in=[event.source_event_id for event in events], org_id=org_id,
        )
    }
    accounts = {
        account.id: {
            'id': str(account.id), 'name': account.name, 'username': account.username,
            'asset': {'name': account.asset.name, 'address': account.asset.address},
        }
        for account in Account.objects.filter(
            id__in=[audit.account_id for audit in audits.values() if audit.account_id],
            org_id=org_id,
        ).select_related('asset')
    }
    return audits, accounts


def _summary(events, audits, accounts):
    events = _ordered(events)
    first, last = events[0], events[-1]
    audit = next((audits.get(event.source_event_id) for event in events
                  if audits.get(event.source_event_id)), None)
    rotation = first.rotation
    codes = [event.event for event in events]
    if rotation:
        kind = 'rotation'
        status = rotation.status
        if status == 'running' and last.event in (
            ApplicationEvent.ROTATION_FAILED, ApplicationEvent.CREDENTIAL_CHANGE_FAILED,
        ):
            status = 'failed'
    elif audit and audit.event == AuditEvent.CREDENTIAL_REPUBLISHED:
        kind = 'subscription_refresh'
        status = 'published'
    elif any(code.startswith('credential.change.') for code in codes):
        kind = 'subscription' if audit and audit.operation_id else 'legacy'
        status = {
            ApplicationEvent.CREDENTIAL_CHANGE_FAILED: 'failed',
            ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED: 'success',
            ApplicationEvent.CREDENTIAL_UPDATED: 'success',
        }.get(last.event, 'running')
    else:
        kind = 'update' if audit and audit.operation_id else 'event'
        status = 'published'
    cycle_accounts = {}
    for event in events:
        source = audits.get(event.source_event_id)
        if source and source.account_id:
            cycle_accounts[str(source.account_id)] = accounts.get(source.account_id) or {
                'id': str(source.account_id), 'name': source.account,
            }
    account = accounts.get(audit.account_id) if audit else None
    if audit and audit.account_id and not account:
        account = {'id': str(audit.account_id), 'name': audit.account}
    return {
        'id': str(first.cycle_key), 'kind': kind, 'status': status,
        'rotation_id': str(first.rotation_id) if first.rotation_id else None,
        'date_started': first.published_at.isoformat(),
        'date_last_event': last.published_at.isoformat(),
        'event_count': len(events), 'account': account, 'accounts': list(cycle_accounts.values()),
        'latest_event': last.event,
    }


def cycle_directory(credential, limit=20, offset=0, *, kind='', status='', started_after=None, started_before=None):
    queryset = policy_events(credential)
    groups = queryset.values('cycle_key').annotate(
        date_started=Min('published_at'), date_last_event=Max('published_at'),
        event_count=Count('id'),
        rotation_status=Max('rotation__status'),
    )
    related = queryset.filter(cycle_key=OuterRef('cycle_key')).order_by()
    source = ApplicationAudit.objects.filter(id__in=queryset.filter(
        cycle_key=OuterRef(OuterRef('cycle_key')),
    ).order_by().values('source_event_id'))
    # Keep correlated expressions inside aggregates: otherwise Django expands
    # GROUP BY to the event's source ID and splits a cycle into individual rows.
    groups = groups.annotate(
        last_code=Max(Subquery(related.order_by('-sequence', '-published_at', '-id').values('event')[:1])),
        has_change=Count('id', filter=Q(event__startswith='credential.change.')),
        republished=Max(Cast(Exists(source.filter(event=AuditEvent.CREDENTIAL_REPUBLISHED)), IntegerField())),
        has_operation=Max(Cast(Exists(source.filter(operation_id__isnull=False)), IntegerField())),
    ).annotate(
        kind=Case(
            When(rotation_status__isnull=False, then=Value('rotation')),
            When(republished=1, then=Value('subscription_refresh')),
            When(has_change__gt=0, has_operation=1, then=Value('subscription')),
            When(has_change__gt=0, then=Value('legacy')),
            When(has_operation=1, then=Value('update')),
            default=Value('event'), output_field=CharField(),
        ),
        status=Case(
            When(rotation_status='running', last_code__in=(
                ApplicationEvent.ROTATION_FAILED, ApplicationEvent.CREDENTIAL_CHANGE_FAILED,
            ), then=Value('failed')),
            When(rotation_status__isnull=False, then='rotation_status'),
            When(republished=1, then=Value('published')),
            When(has_change__gt=0, last_code=ApplicationEvent.CREDENTIAL_CHANGE_FAILED, then=Value('failed')),
            When(has_change__gt=0, last_code__in=(
                ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, ApplicationEvent.CREDENTIAL_UPDATED,
            ), then=Value('success')),
            When(has_change__gt=0, then=Value('running')),
            default=Value('published'), output_field=CharField(),
        ),
    )
    if kind:
        groups = groups.filter(kind=kind)
    if status:
        groups = groups.filter(status=status)
    if started_after:
        groups = groups.filter(date_started__gte=started_after)
    if started_before:
        groups = groups.filter(date_started__lte=started_before)
    groups = groups.order_by('-date_started', '-cycle_key')
    count = groups.count()
    cycle_ids = [item['cycle_key'] for item in groups[offset:offset + limit]]
    events = list(queryset.filter(cycle_key__in=cycle_ids).select_related('rotation'))
    audits, accounts = _context(events, credential.org_id)
    by_cycle = defaultdict(list)
    for event in events:
        by_cycle[event.cycle_key].append(event)
    current_rotation = credential.rotation_records.filter(
        status__in=('preparing', 'running'), date_finished__isnull=True,
    ).first()
    current = list(queryset.filter(rotation=current_rotation).select_related('rotation')) if current_rotation else []
    current_audits, current_accounts = _context(current, credential.org_id) if current else ({}, {})
    return {
        'count': count,
        'results': [_summary(by_cycle[key], audits, accounts) for key in cycle_ids],
        'current_cycle': _summary(current, current_audits, current_accounts) if current else None,
        'retention_days': get_log_keep_day('APPLICATION_RECORD_KEEP_DAYS'),
    }


def cycle_detail(credential, cycle_id):
    from .preparation import cycle_info
    from .source_traffic import info as source_traffic_info
    events = _ordered(list(policy_events(credential).filter(
        cycle_key=cycle_id,
    ).select_related('rotation')))
    if not events:
        raise NotFound()
    audits, accounts = _context(events, credential.org_id)
    summary = _summary(events, audits, accounts)
    rotation = events[0].rotation
    preparation = cycle_info(credential, rotation)
    observations = (rotation.participant_snapshot.get('preparation', {}).get('event_observations', {})
                    if rotation else {})
    traffic_snapshot = (rotation.participant_snapshot.get('source_traffic', {}) if rotation else {})
    source_traffic = (source_traffic_info(credential, rotation) if rotation else None) or traffic_snapshot.get('final')
    traffic_observations = traffic_snapshot.get('event_observations', {})
    clients = {
        str(client.id): client for client in CredentialClientInstance.objects.filter(
            id__in={row['id'] for event in events for row in event.recipients},
            org_id=credential.org_id,
        ).select_related('application')
    }
    confirmations = ApplicationAudit.objects.filter(
        credential_id=credential.id, org_id=credential.org_id,
        event=AuditEvent.CREDENTIAL_CONFIRMED, result='success',
        revision__in=[event.revision for event in events],
    ).order_by('date_created', 'id')
    if events[0].rotation_id:
        confirmations = confirmations.filter(rotation_id=events[0].rotation_id)
    confirmed = {}
    for audit in confirmations:
        identity = (str(audit.service_id), audit.source.lower(), audit.instance_id, audit.revision)
        confirmed.setdefault(identity, audit.date_created.isoformat())
    rows = []
    for sequence, event in enumerate(events, start=1):
        audit = audits.get(event.source_event_id)
        requires_confirmation = (
            (event.rotation_id is not None or credential.mode == credential.Mode.alternating_rotation)
            and event.event == ApplicationEvent.CREDENTIAL_UPDATED
        )
        recipients = []
        for recipient in event.recipients:
            client = clients.get(recipient['id'])
            active = bool(
                client and client.is_valid
                and str(client.application_id) == recipient['application']['id']
            )
            identity = (
                recipient['application']['id'], recipient['type'], recipient['instance_id'], event.revision,
            )
            recipients.append({
                **recipient, 'is_active': active, 'online': bool(active and client.online),
                'confirmed_at': confirmed.get(identity) if requires_confirmation else None,
            })
        rows.append({
            'id': str(event.source_event_id), 'event': event.event, 'sequence': sequence,
            'published_at': event.published_at.isoformat(), 'revision': event.revision,
            'result': audit.result if audit else None,
            'account_id': str(audit.account_id) if audit and audit.account_id else None,
            'account': accounts.get(audit.account_id) if audit else None,
            'preparation': observations.get(str(event.source_event_id)),
            'source_traffic': traffic_observations.get(str(event.source_event_id)),
            'requires_confirmation': requires_confirmation,
            'recipient_count': len(recipients),
            'received_count': sum(bool(item['received_at']) for item in recipients),
            'confirmed_count': sum(bool(item['confirmed_at']) for item in recipients),
            'recipients': recipients,
        })
    return {**summary, 'preparation': preparation, 'source_traffic': source_traffic, 'events': rows}
