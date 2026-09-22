from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import (
    ApplicationCredential, ClientAccessConfiguration, CredentialApplicationBinding,
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
    configuration = client.configuration
    return {
        'application': {'id': str(application.id), 'name': application.name},
        'configuration': {'id': str(configuration.id), 'name': configuration.name},
        'client': {
            'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
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
            'status', 'blocking',
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
        status='running', date_finished__isnull=True,
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
    credentials = ApplicationCredential.objects.select_for_update().filter(
        access_configurations=client.configuration,
    ).exclude(status=ApplicationCredential.Status.idle).order_by('id')
    for credential in credentials:
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
        status='running', date_finished__isnull=True,
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
    if excluded:
        name = 'excluded'
    elif not online:
        name = 'offline'
    elif (
        state.applied_account_id == desired_account.id
        and state.applied_revision == required_revision
    ):
        name = 'switched'
    elif max(state.fetched_revision, state.delivered_revision) >= required_revision:
        name = 'awaiting_confirmation'
    elif source_account and state.applied_account_id == source_account.id:
        name = 'using_source'
    elif state.applied_account_id == desired_account.id:
        name = 'stale_confirmation'
    else:
        name = 'unknown'
    blocking = not excluded and credential.status in BLOCKING_PHASES and name != 'switched'
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
        'status': name,
        'blocking': blocking,
    }


def _warnings(credential):
    warnings = []
    configurations = ClientAccessConfiguration.objects.filter(
        credentials=credential, is_active=True, application__is_active=True,
    ).select_related('application').distinct()
    for configuration in configurations:
        if configuration.instances.filter(is_active=True).exists():
            continue
        warnings.append({
            'code': 'no_active_instance',
            'application': {
                'id': str(configuration.application_id),
                'name': configuration.application.name,
            },
            'configuration': {'id': str(configuration.id), 'name': configuration.name},
        })
    return warnings


def _application_summary(instances, warnings):
    applications = {}
    for item in instances:
        application = item['application']
        summary = applications.setdefault(application['id'], {
            'application': application, 'total': 0, 'switched': 0, 'blocking': 0,
            'status': 'not_switched',
        })
        if item['status'] == 'excluded':
            continue
        summary['total'] += 1
        summary['switched'] += item['status'] == 'switched'
        summary['blocking'] += item['blocking']
    for warning in warnings:
        application = warning['application']
        applications.setdefault(application['id'], {
            'application': application, 'total': 0, 'switched': 0, 'blocking': 0,
            'status': 'no_instance',
        })
    for item in applications.values():
        if not item['total']:
            item['status'] = 'no_instance'
        elif item['switched'] == item['total']:
            item['status'] = 'all_switched'
        elif item['switched']:
            item['status'] = 'partially_switched'
        else:
            item['status'] = 'not_switched'
    return sorted(applications.values(), key=lambda item: item['application']['name'])


def build(credential, rotation=None, now=None):
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
        'binding__application', 'client__configuration', 'applied_account',
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
            'switched', 'using_source', 'awaiting_confirmation', 'stale_confirmation',
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
    return {
        'rotation_id': str(rotation.id) if rotation else None,
        'credential_status': credential.status,
        'source_account': _account(rotation.source_account) if rotation else None,
        'switch_source_account': _account(
            rotation.target_account
            if rotation and credential.active_account_id == rotation.source_account_id
            else rotation.source_account if rotation else None
        ),
        'target_account': _account(rotation.target_account) if rotation else None,
        'desired_account': _account(credential.active_account),
        'change_account': _account(rotation.change_account) if rotation else None,
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
    rotation.participant_snapshot = snapshot
    rotation.save(update_fields=['participant_snapshot', 'date_updated'])
    return status
