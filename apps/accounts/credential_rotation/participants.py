from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Max

from accounts.const import AuditEvent
from accounts.models import (
    ApplicationAudit, ApplicationCredential, CredentialApplicationBinding,
    CredentialClientStatus,
)


SNAPSHOT_VERSION = 1
BLOCKING_PHASES = {
    ApplicationCredential.Status.waiting_switch,
    ApplicationCredential.Status.ready_for_change,
    ApplicationCredential.Status.change_failed,
    ApplicationCredential.Status.recovery_required,
    ApplicationCredential.Status.waiting_revert,
}


def _date(value):
    return value.isoformat() if value else None


def _account(account):
    if not account:
        return None
    return {
        'id': str(account.id),
        'name': account.name,
        'username': account.username,
    }


def _participant(state, joined_during_rotation=False):
    client = state.client
    application = state.binding.application
    return {
        'application': {'id': str(application.id), 'name': application.name},
        'client': {
            'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
            'supports_receipts': client.event_receipts_supported,
        },
        'joined_at': _date(timezone.now()),
        'joined_during_rotation': joined_during_rotation,
        'excluded_at': None,
        'exclusion_reason': '',
        'final': None,
    }


def _final_state(item):
    return {
        key: item.get(key) for key in (
            'online', 'applied_account', 'desired_account', 'fetched_revision',
            'delivered_revision', 'applied_revision', 'required_revision',
            'date_last_seen', 'date_fetched', 'date_delivered', 'date_applied',
            'status', 'blocking', 'confirmation_skipped', 'application_failure',
        )
    }


def initialize(rotation, states):
    rotation.participant_snapshot = {
        'version': SNAPSHOT_VERSION,
        'participants': [_participant(state) for state in states],
        'warnings': [],
        'summary': {},
    }
    rotation.save(update_fields=['participant_snapshot', 'date_updated'])


def ensure_participant(credential, state):
    rotation = credential.rotation_records.filter(
        status__in=('running', 'preparing'), date_finished__isnull=True,
    ).first()
    if not rotation:
        return
    snapshot = rotation.participant_snapshot or {}
    participants = snapshot.setdefault('participants', [])
    client_id = str(state.client_id)
    if any(
        item['client']['id'] == client_id and not item.get('excluded_at')
        for item in participants
    ):
        return
    participants.append(_participant(state, joined_during_rotation=True))
    snapshot['version'] = SNAPSHOT_VERSION
    rotation.participant_snapshot = snapshot
    rotation.save(update_fields=['participant_snapshot', 'date_updated'])


@transaction.atomic
def enroll_client(client):
    from accounts.credential_client.manager import client_uses_credential

    credentials = ApplicationCredential.objects.select_for_update().filter(
        applications=client.application,
    ).exclude(status=ApplicationCredential.Status.idle).order_by('id')
    for credential in credentials:
        if not client_uses_credential(client, credential):
            continue
        binding = CredentialApplicationBinding.objects.filter(
            credential=credential, application=client.application,
        ).first()
        if not binding:
            continue
        state, _ = CredentialClientStatus.objects.get_or_create(
            binding=binding, client=client,
        )
        if not state.is_rotation_participant or state.required_revision != credential.revision:
            state.is_rotation_participant = True
            state.required_revision = credential.revision
            state.save(update_fields=[
                'is_rotation_participant', 'required_revision', 'date_updated',
            ])
        ensure_participant(credential, state)


def exclude(credential, states, reason):
    rotation = credential.rotation_records.filter(
        status__in=('running', 'preparing'), date_finished__isnull=True,
    ).first()
    if not rotation:
        return
    snapshot = rotation.participant_snapshot or {}
    participants = snapshot.setdefault('participants', [])
    now = _date(timezone.now())
    for state in states:
        client_id = str(state.client_id)
        item = next((
            candidate for candidate in reversed(participants)
            if candidate['client']['id'] == client_id and not candidate.get('excluded_at')
        ), None)
        if not item:
            item = _participant(state, joined_during_rotation=True)
            participants.append(item)
        item.update(excluded_at=now, exclusion_reason=reason)
        item['final'] = _final_state(
            _state(credential, rotation, item, state, timezone.now())
        )
    snapshot['version'] = SNAPSHOT_VERSION
    rotation.participant_snapshot = snapshot
    rotation.save(update_fields=['participant_snapshot', 'date_updated'])


def _state(credential, rotation, participant, state, now):
    excluded = bool(participant.get('excluded_at'))
    required_revision = (
        state.required_revision or credential.revision
        if state else credential.revision
    )
    desired_account = credential.active_account
    source_account = None
    if rotation:
        source_account = (
            rotation.target_account
            if credential.active_account_id == rotation.source_account_id
            else rotation.source_account
        )
    client = state.client if state else None
    online = bool(
        client and client.is_active and client.date_last_seen
        and client.date_last_seen >= now - timedelta(minutes=2)
    )
    applied_account = state.applied_account if state else None
    failure = state.application_failure if state else {}
    current_failure = failure and failure.get('revision') == required_revision
    if excluded:
        name = 'excluded'
    elif current_failure and failure.get('review_required'):
        name = 'review_required'
    elif current_failure and failure.get('reviewed_at'):
        name = 'approved'
    elif not online:
        name = 'offline'
    elif (
        state.applied_account_id == desired_account.id
        and state.applied_revision == required_revision
    ):
        name = 'skipped' if state.confirmation_skipped else 'switched'
    elif max(state.fetched_revision, state.delivered_revision) >= required_revision:
        name = 'awaiting_confirmation'
    elif source_account and state.applied_account_id == source_account.id:
        name = 'using_source'
    elif state.applied_account_id == desired_account.id:
        name = 'stale_confirmation'
    else:
        name = 'unknown'
    blocking = not excluded and (
        credential.status in BLOCKING_PHASES and name not in ('switched', 'skipped', 'approved')
        or name == 'review_required' and credential.status != credential.Status.idle
    )
    return {
        **participant,
        'online': online,
        'applied_account': _account(applied_account),
        'desired_account': _account(desired_account),
        'fetched_revision': state.fetched_revision if state else 0,
        'delivered_revision': state.delivered_revision if state else 0,
        'applied_revision': state.applied_revision if state else 0,
        'required_revision': required_revision,
        'date_last_seen': _date(client.date_last_seen) if client else None,
        'date_fetched': _date(state.date_fetched) if state else None,
        'date_delivered': _date(state.date_delivered) if state else None,
        'date_applied': _date(state.date_applied) if state else None,
        'confirmation_skipped': bool(state and state.confirmation_skipped),
        'application_failure': failure if current_failure else {},
        'status': name,
        'blocking': blocking,
    }


def _warnings(credential):
    warnings = []
    for application in credential.applications.filter(is_active=True):
        if application.credential_clients.filter(is_active=True).exclude(type='sdk', rotation_enabled=False).exists():
            continue
        warnings.append({
            'code': 'no_active_instance',
            'application': {
                'id': str(application.id),
                'name': application.name,
            },
        })
    return warnings


def _application_summary(instances, warnings):
    applications = {}
    for item in instances:
        application = item['application']
        summary = applications.setdefault(application['id'], {
            'application': application, 'total': 0, 'switched': 0, 'skipped': 0, 'approved': 0, 'blocking': 0,
            'status': 'not_switched',
        })
        if item['status'] == 'excluded':
            continue
        summary['total'] += 1
        summary['switched'] += item['status'] == 'switched'
        summary['skipped'] += item['status'] == 'skipped'
        summary['approved'] += item['status'] == 'approved'
        summary['blocking'] += item['blocking']
    for warning in warnings:
        application = warning['application']
        applications.setdefault(application['id'], {
            'application': application, 'total': 0, 'switched': 0, 'skipped': 0, 'approved': 0, 'blocking': 0,
            'status': 'no_instance',
        })
    for item in applications.values():
        if not item['total']:
            item['status'] = 'no_instance'
        elif item['approved'] and item['switched'] + item['skipped'] + item['approved'] == item['total']:
            item['status'] = 'all_processed'
        elif item['skipped'] == item['total']:
            item['status'] = 'all_skipped'
        elif item['switched'] + item['skipped'] == item['total'] and item['skipped']:
            item['status'] = 'all_processed'
        elif item['switched'] == item['total']:
            item['status'] = 'all_switched'
        elif item['switched']:
            item['status'] = 'partially_switched'
        else:
            item['status'] = 'not_switched'
    return sorted(applications.values(), key=lambda item: item['application']['name'])




def build(credential, rotation=None, now=None):
    from .source_traffic import info as source_traffic_info

    now = now or timezone.now()
    rotation = rotation or credential.rotation_records.select_related(
        'source_account', 'target_account', 'change_account',
    ).first()
    snapshot = rotation.participant_snapshot if rotation else {}
    participants = list((snapshot or {}).get('participants', []))
    states = CredentialClientStatus.objects.filter(
        binding__credential=credential,
        client_id__in=[item['client']['id'] for item in participants],
    ).select_related(
        'binding__application', 'applied_account',
    )
    by_client = {str(state.client_id): state for state in states}
    instances = [
        _state(credential, rotation, item, by_client.get(item['client']['id']), now)
        for item in participants
    ]
    instances.sort(key=lambda item: (
        not item['blocking'], item['application']['name'], item['client']['instance_id'],
    ))
    warnings = _warnings(credential) if credential.status != credential.Status.idle else []
    counts = Counter(item['status'] for item in instances)
    summary = {
        'total': len(instances),
        'blocking': sum(item['blocking'] for item in instances),
        **{name: counts[name] for name in (
            'switched', 'skipped', 'approved', 'review_required', 'using_source', 'awaiting_confirmation', 'stale_confirmation',
            'offline', 'unknown', 'excluded',
        )},
    }
    blockers = [{
        'application': item['application'],
        'client': item['client'],
        'reason': item['status'],
        'applied_revision': item['applied_revision'],
        'required_revision': item['required_revision'],
        'applied_account': (item['applied_account'] or {}).get('id', ''),
        'date_last_seen': item['date_last_seen'],
    } for item in instances if item['blocking']]
    traffic = source_traffic_info(credential, rotation, now)
    return {
        'rotation_id': str(rotation.id) if rotation else None,
        'credential_status': credential.status,
        # The switch state also covers the source-account observation window.
        # Keep the workflow state stable, but expose the actual waiting phase.
        'rotation_phase': (
            'waiting_source'
            if credential.status == credential.Status.waiting_switch and not blockers and traffic
            else credential.status
        ),
        'source_account': _account(rotation.source_account) if rotation else None,
        'switch_source_account': _account(
            rotation.target_account
            if rotation and credential.active_account_id == rotation.source_account_id
            else rotation.source_account if rotation else None
        ),
        'target_account': _account(rotation.target_account) if rotation else None,
        'desired_account': _account(credential.active_account),
        'change_account': _account(rotation.change_account) if rotation else None,
        'source_traffic': traffic,
        'required_revision': credential.revision,
        'summary': summary,
        'applications': _application_summary(instances, warnings),
        'instances': instances,
        'warnings': warnings,
        'blockers': blockers,
    }


def finalize(credential, rotation):
    status = build(credential, rotation)
    snapshot = rotation.participant_snapshot or {'version': SNAPSHOT_VERSION, 'participants': []}
    by_client = {item['client']['id']: item for item in status['instances']}
    for participant in snapshot['participants']:
        if participant.get('excluded_at') and participant.get('final'):
            continue
        item = by_client.get(participant['client']['id'])
        participant['final'] = _final_state(item) if item else None
    snapshot['warnings'] = status['warnings']
    snapshot['summary'] = status['summary']
    snapshot['applications'] = status['applications']
    if status['source_traffic'] and snapshot.get('source_traffic'):
        snapshot['source_traffic']['final'] = status['source_traffic']
    rotation.participant_snapshot = snapshot
    rotation.save(update_fields=['participant_snapshot', 'date_updated'])
    return status
