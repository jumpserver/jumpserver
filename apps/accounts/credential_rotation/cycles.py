"""Policy-owned event cycles and their frozen, per-event recipient receipts."""
from collections import defaultdict

from django.db.models import Case, CharField, Count, Exists, IntegerField, Max, Min, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Cast, Coalesce
from rest_framework.exceptions import NotFound
from django.utils.dateparse import parse_datetime

from accounts.const import ApplicationEvent, AuditEvent
from accounts.models import Account, ApplicationAudit, CredentialClientInstance, CredentialClientStatus, CredentialRotationEvent
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


def event_account_data(events, org_id):
    audits = {
        audit.id: audit for audit in ApplicationAudit.objects.filter(
            id__in=[event.source_event_id for event in events], org_id=org_id,
        )
    }
    account_ids = {audit.account_id for audit in audits.values() if audit.account_id}
    for event in events:
        if event.rotation_id:
            account_ids.update((
                event.rotation.source_account_id, event.rotation.target_account_id,
                event.rotation.change_account_id,
            ))
    accounts = {
        account.id: {
            'id': str(account.id), 'name': account.name, 'username': account.username,
            'asset': {'name': account.asset.name, 'address': account.asset.address},
        }
        for account in Account.objects.filter(
            id__in=account_ids,
            org_id=org_id,
        ).select_related('asset')
    }
    return audits, accounts


def _rotation_accounts(rotation, accounts):
    if not rotation:
        return None
    return {
        role: accounts.get(getattr(rotation, f'{role}_account_id'))
        for role in ('source', 'target', 'change')
    }


def event_account_context(event, audit, accounts, published_account=None):
    rotation = event.rotation
    rotation_accounts = _rotation_accounts(rotation, accounts)
    if not rotation_accounts:
        return {}
    account_change = next((
        change for change in (audit.changes if audit else [])
        if change['field'] == 'active_account_id'
    ), None)
    published_id = account_change['after'] if account_change else None
    if not published_id:
        published_id = next((
            item['account_id'] for item in event.recipients if item.get('account_id')
        ), None)
    if published_id:
        published_account = next((
            account for account in rotation_accounts.values()
            if account and account['id'] == str(published_id)
        ), None)
    elif event.event == ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED:
        reverting = audit and audit.event == AuditEvent.ROTATION_CANCELLED
        published_account = rotation_accounts['source' if reverting else 'target']
    elif event.event in (ApplicationEvent.ROTATION_STARTED, ApplicationEvent.ROTATION_WAITING):
        published_account = rotation_accounts['target']
    account_switch = None
    if published_account and event.event == ApplicationEvent.CREDENTIAL_SWITCH_PUBLISHED:
        reverting = published_account['id'] == str(rotation.source_account_id)
        account_switch = {
            'from_account': rotation_accounts['target' if reverting else 'source'],
            'to_account': published_account,
            'reverting': reverting,
        }
    return {
        'rotation_accounts': rotation_accounts,
        'published_account': published_account,
        'account_switch': account_switch,
    }


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
        kind = 'subscription'
        status = {
            ApplicationEvent.CREDENTIAL_CHANGE_FAILED: 'failed',
            ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED: 'success',
            ApplicationEvent.CREDENTIAL_SECRET_UPDATED: 'success',
        }.get(last.event, 'running')
    else:
        kind = 'update' if audit and audit.operation_id else 'event'
        status = 'published'
    cycle_accounts = {}
    rotation_accounts = _rotation_accounts(rotation, accounts)
    if rotation_accounts:
        cycle_accounts.update({
            account['id']: account for account in rotation_accounts.values() if account
        })
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
        'rotation_accounts': rotation_accounts,
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
            When(has_change__gt=0, then=Value('subscription')),
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
                ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, ApplicationEvent.CREDENTIAL_SECRET_UPDATED,
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
    audits, accounts = event_account_data(events, credential.org_id)
    by_cycle = defaultdict(list)
    for event in events:
        by_cycle[event.cycle_key].append(event)
    current_rotation = credential.rotation_records.filter(
        status__in=('preparing', 'running'), date_finished__isnull=True,
    ).first()
    current = list(queryset.filter(rotation=current_rotation).select_related('rotation')) if current_rotation else []
    current_audits, current_accounts = event_account_data(current, credential.org_id) if current else ({}, {})
    return {
        'count': count,
        'results': [_summary(by_cycle[key], audits, accounts) for key in cycle_ids],
        'current_cycle': _summary(current, current_audits, current_accounts) if current else None,
        'retention_days': get_log_keep_day('APPLICATION_RECORD_KEEP_DAYS'),
    }


def cycle_detail(credential, cycle_id):
    from .participants import build
    from .source_traffic import info as source_traffic_info, observation_in_minutes
    events = _ordered(list(policy_events(credential).filter(
        cycle_key=cycle_id,
    ).select_related('rotation')))
    if not events:
        raise NotFound()
    audits, accounts = event_account_data(events, credential.org_id)
    summary = _summary(events, audits, accounts)
    rotation = events[0].rotation
    # Events record publication order; they do not prove that a waiting step
    # has finished. Use the same live progress as the policy list for open cycles.
    rotation_status = None
    if rotation and not rotation.date_finished:
        progress = build(credential, rotation)
        rotation_status = {
            key: progress[key] for key in ('credential_status', 'rotation_phase', 'summary')
        }
    traffic_snapshot = (rotation.participant_snapshot.get('source_traffic', {}) if rotation else {})
    source_traffic = (source_traffic_info(credential, rotation) if rotation else None) or observation_in_minutes(
        traffic_snapshot.get('final'),
    )
    traffic_observations = traffic_snapshot.get('event_observations', {})
    clients = {
        str(client.id): client for client in CredentialClientInstance.objects.filter(
            id__in={row['id'] for event in events for row in event.recipients},
            org_id=credential.org_id,
        ).select_related('application')
    }
    confirmations = ApplicationAudit.objects.filter(
        credential_id=credential.id, org_id=credential.org_id,
        event__in=(AuditEvent.CREDENTIAL_CONFIRMED, AuditEvent.CREDENTIAL_CONFIRMATION_SKIPPED), result='success',
        revision__in=[event.revision for event in events],
    ).order_by('date_created', 'id')
    if events[0].rotation_id:
        confirmations = confirmations.filter(rotation_id=events[0].rotation_id)
    confirmed, skipped = {}, {}
    for audit in confirmations:
        identity = (str(audit.service_id), audit.source.lower(), audit.instance_id, audit.revision)
        results = skipped if audit.event == AuditEvent.CREDENTIAL_CONFIRMATION_SKIPPED else confirmed
        results.setdefault(identity, audit.date_created.isoformat())
    failure_reviews = {}
    for event in events:
        for recipient in event.recipients:
            if recipient.get('failure_review'):
                failure_reviews[(recipient['id'], event.revision)] = recipient['failure_review']
    for state in CredentialClientStatus.objects.filter(binding__credential=credential, client_id__in=clients):
        if state.application_failure:
            failure_reviews[(str(state.client_id), state.application_failure['revision'])] = state.application_failure
    rows = []
    rotation_accounts = summary['rotation_accounts']
    published_account = rotation_accounts['source'] if rotation_accounts else None
    for sequence, event in enumerate(events, start=1):
        audit = audits.get(event.source_event_id)
        # Event selectors and the ordered cycle preserve historical switch direction.
        context = event_account_context(event, audit, accounts, published_account)
        published_account = context.get('published_account')
        requires_confirmation = (
            (event.rotation_id is not None or credential.mode == credential.Mode.alternating_rotation)
            and event.event in ApplicationEvent.credential_application_events()
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
            failure_review = failure_reviews.get((recipient['id'], event.revision), {}) if requires_confirmation else {}
            if failure_review:
                failure_review = {**failure_review, 'can_review': bool(
                    failure_review.get('review_required') and failure_review.get('revision') == credential.current_revision
                )}
            confirmed_at = confirmed.get(identity) if requires_confirmation else None
            skipped_at = skipped.get(identity) if requires_confirmation and identity not in confirmed else None
            if failure_review:
                failed_at = parse_datetime(failure_review['failed_at'])
                if confirmed_at and parse_datetime(confirmed_at) <= failed_at:
                    confirmed_at = None
                if skipped_at and parse_datetime(skipped_at) <= failed_at:
                    skipped_at = None
            recipients.append({
                **recipient, 'failure_review': failure_review, 'is_active': active, 'online': bool(active and client.online),
                'confirmed_at': confirmed_at,
                'skipped_at': skipped_at,
            })
        rows.append({
            'id': str(event.source_event_id), 'event': event.event, 'sequence': sequence,
            'published_at': event.published_at.isoformat(), 'revision': event.revision,
            'result': audit.result if audit else None,
            'account_id': str(audit.account_id) if audit and audit.account_id else None,
            'account': accounts.get(audit.account_id) if audit else None,
            **context,
            'source_traffic': observation_in_minutes(traffic_observations.get(str(event.source_event_id))),
            'requires_confirmation': requires_confirmation,
            'recipient_count': len(recipients),
            'received_count': sum(bool(item['received_at']) for item in recipients),
            'confirmed_count': sum(bool(item['confirmed_at']) for item in recipients),
            'skipped_count': sum(bool(item['skipped_at']) for item in recipients),
            'review_required_count': sum(bool(item['failure_review'].get('review_required')) for item in recipients),
            'admin_approved_count': sum(bool(item['failure_review'].get('reviewed_at')) for item in recipients),
            'recipients': recipients,
        })
    return {
        **summary, 'rotation_status': rotation_status,
        'source_traffic': source_traffic, 'events': rows,
    }
