"""Administrator-triggered account alignment; traffic means Secret API access."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue
from accounts.models import (
    Account, ApplicationAudit, ApplicationCredential, CredentialApplicationBinding,
    CredentialClientInstance, CredentialClientStatus, CredentialRotationRecord,
)
from common.exceptions import JMSException

PHASES = ('preparing', 'waiting_standby', 'ready_to_switch')


def _emit(credential, rotation, code, summary=''):
    event = record(AuditEvent.ROTATION_STEP, credential=credential, summary=summary)
    meta = rotation.participant_snapshot.get('preparation')
    if meta:
        meta.setdefault('event_observations', {})[str(event.id)] = _observation(credential, rotation)
        rotation.save(update_fields=['participant_snapshot'])
    enqueue(event, code, rotation=rotation)


def _observation(credential, rotation):
    meta = rotation.participant_snapshot.get('preparation', {})
    current = rotation.status == 'preparing' and credential.status in PHASES and not rotation.date_finished
    days = meta.get('standby_no_traffic_days', credential.standby_no_traffic_days if current else None)
    idle_since = parse_datetime(meta['standby_idle_since']) if meta.get('standby_idle_since') else None
    account = meta.get('standby_account')
    if not account:
        target = rotation.target_account
        account = {'id': str(target.id), 'name': target.name, 'username': target.username}
    return {
        'status': meta.get('status', credential.status if current else None),
        'standby_account': account, 'standby_no_traffic_days': days,
        'aligned_at': meta.get('aligned_at'),
        'standby_last_access': meta.get('standby_last_access'),
        'standby_idle_since': meta.get('standby_idle_since'),
        'eligible_at': (idle_since + timedelta(days=days)).isoformat() if idle_since and days else None,
        'ready_at': meta.get('ready_at'),
    }


def cycle_info(credential, rotation):
    if not rotation or not rotation.participant_snapshot.get('preparation'):
        return None
    info = _observation(credential, rotation)
    current = rotation.status == 'preparing' and credential.status in PHASES and not rotation.date_finished
    info['is_current'] = current
    if rotation.status == 'cancelled':
        info['status'] = 'cancelled'
    elif current:
        info['status'] = credential.status
    elif info['ready_at']:
        info['status'] = 'completed'
    else:
        info['status'] = info['status'] or 'completed'
    eligible_at = parse_datetime(info['eligible_at']) if info['eligible_at'] else None
    info['remaining_seconds'] = max(0, (eligible_at - timezone.now()).total_seconds()) if current and eligible_at else None
    return info


def start(credential, operator='', operator_id=None):
    from .participants import initialize
    from .preflight import check
    from accounts.credential_client.manager import client_uses_credential
    if credential.status != credential.Status.idle:
        raise JMSException(_('Only idle policies can start rotation preparation.'))
    check(credential)
    clients = CredentialClientInstance.objects.filter(
        application__credential_bindings__credential=credential,
        application__is_active=True, is_active=True,
    ).select_related('application').distinct()
    for client in clients:
        if not client_uses_credential(client, credential):
            continue
        binding = CredentialApplicationBinding.objects.get(credential=credential, application=client.application)
        CredentialClientStatus.objects.get_or_create(binding=binding, client=client)
    states = [
        state for state in credential.rotation_statuses().select_for_update(of=('self',)).select_related(
            'binding__application', 'client',
        ) if client_uses_credential(state.client, credential) or state.is_rotation_participant
    ]
    rotation = CredentialRotationRecord.objects.create(
        credential=credential, source_account=credential.active_account,
        target_account=credential.target_account, change_account=credential.active_account,
        change_account_version_at_start=credential.active_account.version,
        status='preparing', created_by=operator,
    )
    initialize(rotation, states)
    rotation.participant_snapshot['preparation'] = {
        'operator_id': str(operator_id) if operator_id else None,
        'started_at': timezone.now().isoformat(), 'aligned_at': None,
        'standby_idle_since': None, 'ready_at': None, 'notified_at': None,
        'applications': [str(value) for value in credential.applications.values_list('id', flat=True)],
        'status': 'preparing', 'standby_no_traffic_days': credential.standby_no_traffic_days,
        'standby_account': {
            'id': str(rotation.target_account_id), 'name': rotation.target_account.name,
            'username': rotation.target_account.username,
            'asset': {'name': rotation.target_account.asset.name, 'address': rotation.target_account.asset.address},
        },
        'standby_last_access': rotation.target_account.date_last_secret_access.isoformat()
        if rotation.target_account.date_last_secret_access else None,
    }
    rotation.save(update_fields=['participant_snapshot'])
    _emit(credential, rotation, ApplicationEvent.ROTATION_PREPARATION_STARTED)
    credential.revision += 1
    credential.status = credential.Status.preparing
    credential.date_rotation_started = timezone.now()
    credential.save(update_fields=['revision', 'status', 'date_rotation_started', 'date_updated'])
    CredentialClientStatus.objects.filter(id__in=[state.id for state in states]).update(
        required_revision=credential.revision, is_rotation_participant=True,
    )
    return credential


def _alignment(credential, rotation):
    snapshot = rotation.participant_snapshot
    meta = snapshot['preparation']
    participants = [item for item in snapshot['participants'] if not item.get('excluded_at')]
    states = {str(state.client_id): state for state in CredentialClientStatus.objects.filter(
        binding__credential=credential, client_id__in=[item['client']['id'] for item in participants],
    )}
    by_application = {}
    for item in participants:
        state = states.get(item['client']['id'])
        by_application.setdefault(item['application']['id'], []).append(bool(
            state and state.applied_revision == credential.revision
            and state.applied_account_id == credential.active_account_id
        ))
    legacy = {str(row['service_id']): row['latest'] for row in ApplicationAudit.objects.filter(
        event=AuditEvent.CREDENTIAL_FETCHED, result='success',
        service_id__in=meta['applications'], account_id=credential.active_account_id,
        credential_id__isnull=True, instance_id='', date_created__gte=parse_datetime(meta['started_at']),
    ).values('service_id').annotate(latest=Max('date_created'))}
    applications = list(credential.applications.all())
    return [{
        'id': str(app.id), 'name': app.name,
        'aligned': bool(app.is_active and (
            all(by_application[str(app.id)]) if str(app.id) in by_application else str(app.id) in legacy
        )),
        'type': 'client' if str(app.id) in by_application else 'api',
    } for app in applications]


def refresh(credential, now=None):
    """Caller locks the policy; no API accesses during the observed window proves inactivity."""
    if credential.status not in PHASES:
        return credential
    now = now or timezone.now()
    rotation = credential.rotation_records.select_for_update().filter(status='preparing').first()
    if not rotation:
        return credential
    meta = rotation.participant_snapshot['preparation']
    meta.setdefault('standby_no_traffic_days', credential.standby_no_traffic_days)
    last_access = Account.objects.filter(id=rotation.target_account_id).values_list(
        'date_last_secret_access', flat=True,
    ).get()
    meta['standby_last_access'] = last_access.isoformat() if last_access else None
    applications = _alignment(credential, rotation)
    aligned = bool(applications) and all(app['aligned'] for app in applications)
    previous = credential.status
    if not aligned:
        meta.update(aligned_at=None, standby_idle_since=None, ready_at=None, notified_at=None)
        credential.status = credential.Status.preparing
    else:
        if not meta['aligned_at']:
            meta['aligned_at'] = now.isoformat()
            _emit(credential, rotation, ApplicationEvent.ROTATION_ACCOUNTS_ALIGNED)
        idle_since = max(parse_datetime(meta['aligned_at']), last_access or parse_datetime(meta['aligned_at']))
        meta['standby_idle_since'] = idle_since.isoformat()
        ready = now >= idle_since + timedelta(days=meta['standby_no_traffic_days'])
        credential.status = credential.Status.ready_to_switch if ready else credential.Status.waiting_standby
        if ready:
            meta['ready_at'] = meta.get('ready_at') or now.isoformat()
        else:
            meta.update(ready_at=None, notified_at=None)
    meta['status'] = credential.status
    if previous != credential.status:
        if credential.status == credential.Status.ready_to_switch:
            _emit(credential, rotation, ApplicationEvent.ROTATION_PREPARATION_READY)
        elif credential.status == credential.Status.waiting_standby:
            _emit(credential, rotation, ApplicationEvent.ROTATION_STANDBY_WAITING)
        credential.save(update_fields=['status', 'date_updated'])
    rotation.save(update_fields=['participant_snapshot'])
    return credential


def require_ready(credential):
    refresh(credential)
    if credential.status != credential.Status.ready_to_switch:
        raise JMSException(
            _('Start preparation and wait for account alignment and the standby no-traffic period.'),
            code='credential_preparation_not_ready',
        )


def info(credential):
    if credential.status not in PHASES:
        return None
    rotation = credential.rotation_records.filter(status='preparing').select_related('target_account').first()
    if not rotation:
        return None
    meta = rotation.participant_snapshot.get('preparation', {})
    idle_since = parse_datetime(meta['standby_idle_since']) if meta.get('standby_idle_since') else None
    return {
        'operation_id': str(rotation.id), 'status': credential.status,
        'aligned_at': meta.get('aligned_at'), 'standby_account_id': str(rotation.target_account_id),
        'standby_account': rotation.target_account.username,
        'standby_no_traffic_days': credential.standby_no_traffic_days,
        'standby_last_access': rotation.target_account.date_last_secret_access,
        'standby_idle_since': meta.get('standby_idle_since'),
        'eligible_at': (idle_since + timedelta(days=credential.standby_no_traffic_days)).isoformat() if idle_since else None,
        'ready_at': meta.get('ready_at'), 'notified_at': meta.get('notified_at'),
        'applications': _alignment(credential, rotation),
    }


@transaction.atomic
def record_secret_access(account, application=None):
    # Every successful fetch, including unchanged-revision SDK pulls, resets
    # the source-account observation window. The policy lock serializes it
    # with readiness checks and execution dispatch.
    policies = list(ApplicationCredential.objects.select_for_update(of=('self',)).filter(
        Q(account=account) | Q(alternate_account=account), mode='alternating_rotation',
    ).select_related('account', 'alternate_account', 'active_account').order_by('id'))
    for credential in policies:
        if credential.active_account_id != account.id and credential.status in (
            credential.Status.changing_secret, credential.Status.recovery_required,
        ):
            raise JMSException(
                _('The source account secret is being changed; fetch the active account instead.'),
                code='credential_rotation_source_unavailable',
            )
    now = timezone.now()
    Account.objects.filter(id=account.id).update(date_last_secret_access=now)
    for credential in policies:
        rotation = credential.rotation_records.select_for_update().filter(
            status='running', date_finished__isnull=True,
        ).first()
        if (
            rotation and rotation.source_account_id == account.id
            and credential.status == credential.Status.ready_for_change
        ):
            credential.status = credential.Status.waiting_switch
            credential.save(update_fields=['status', 'date_updated'])
            event = record(
                AuditEvent.ROTATION_STEP, credential=credential, account=account,
                summary='Source account secret was fetched; the no-fetch observation window restarted.',
            )
            from .source_traffic import info as source_traffic_info, remember
            remember(rotation, event, source_traffic_info(credential, rotation, now))
            enqueue(event, ApplicationEvent.ROTATION_SOURCE_WAITING, rotation=rotation)
        if application:
            rotation = credential.rotation_records.select_for_update().filter(status__in=('preparing', 'running')).first()
            if rotation:
                accesses = rotation.participant_snapshot.setdefault('api_accesses', {})
                accesses.setdefault(str(application.id), {})[str(account.id)] = now.isoformat()
                rotation.save(update_fields=['participant_snapshot'])
        refresh(credential, now)


@transaction.atomic
def check(credential_id):
    credential = ApplicationCredential.objects.select_for_update(of=('self',)).select_related(
        'account', 'alternate_account', 'active_account',
    ).get(id=credential_id)
    return refresh(credential)


@transaction.atomic
def notify_ready(credential_id):
    from accounts.notifications import CredentialPreparationReadyMsg
    from users.models import User
    credential = ApplicationCredential.objects.select_for_update().get(id=credential_id)
    refresh(credential)
    if credential.status != credential.Status.ready_to_switch:
        return
    rotation = credential.rotation_records.select_for_update().get(status='preparing')
    meta = rotation.participant_snapshot['preparation']
    if meta.get('notified_at') or not meta.get('operator_id'):
        return
    user = User.objects.filter(id=meta['operator_id'], is_active=True).first()
    if not user or not user.has_perm('accounts.change_applicationcredential'):
        return
    CredentialPreparationReadyMsg(user, credential).publish(is_async=True)
    meta['notified_at'] = timezone.now().isoformat()
    rotation.save(update_fields=['participant_snapshot'])
