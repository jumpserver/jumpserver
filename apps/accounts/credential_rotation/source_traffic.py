"""Observe successful JumpServer secret fetches for the account being replaced."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from accounts.const import ApplicationEvent, AuditEvent
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue
from accounts.models import Account, ApplicationCredential
from common.exceptions import JMSException


def observation_in_minutes(observation):
    if observation and 'no_traffic_days' in observation:
        observation = observation.copy()
        observation['no_traffic_minutes'] = observation.pop('no_traffic_days') * 24 * 60
    return observation


def info(credential, rotation=None, now=None):
    rotation = rotation or credential.rotation_records.first()
    if not rotation or rotation.date_finished or rotation.status != 'running':
        return None
    if credential.active_account_id != rotation.target_account_id:
        return None
    observation = (rotation.participant_snapshot or {}).get('source_traffic', {})
    # Older open cycles began observing at publication. They must establish a
    # new window after application confirmation, without rewriting audit events.
    if (credential.status == credential.Status.waiting_switch
            and not observation.get('switch_confirmed_at')):
        return None
    started_at = parse_datetime(observation['started_at']) if observation.get('started_at') else None
    if not started_at:
        return None
    minutes = observation_in_minutes(observation).get('no_traffic_minutes', credential.source_no_traffic_minutes)
    last_access = Account.objects.filter(id=rotation.source_account_id).values_list(
        'date_last_secret_access', flat=True,
    ).get()
    idle_since = max(started_at, last_access) if last_access else started_at
    eligible_at = idle_since + timedelta(minutes=minutes)
    now = now or timezone.now()
    return {
        'source_account_id': str(rotation.source_account_id),
        'started_at': started_at.isoformat(),
        'no_traffic_minutes': minutes,
        'last_secret_access': last_access.isoformat() if last_access and last_access >= started_at else None,
        'idle_since': idle_since.isoformat(),
        'eligible_at': eligible_at.isoformat(),
        'remaining_seconds': max(0, (eligible_at - now).total_seconds()),
        'ready': now >= eligible_at,
    }


@transaction.atomic
def start_if_ready(credential, rotation=None, now=None):
    credential = ApplicationCredential.objects.select_for_update(of=('self',)).select_related(
        'active_account',
    ).get(pk=credential.pk)
    if credential.status != credential.Status.waiting_switch:
        return None
    rotation = rotation or credential.rotation_records.filter(
        status='running', date_finished__isnull=True,
    ).first()
    if not rotation or credential.active_account_id != rotation.target_account_id:
        return None
    observation = (rotation.participant_snapshot or {}).get('source_traffic', {})
    if observation.get('switch_confirmed_at'):
        return info(credential, rotation, now)
    if credential.get_blockers(now=now):
        return None
    now = now or timezone.now()
    observation = observation_in_minutes(observation)
    observation.update(started_at=now.isoformat(), switch_confirmed_at=now.isoformat())
    observation.setdefault('no_traffic_minutes', credential.source_no_traffic_minutes)
    rotation.participant_snapshot['source_traffic'] = observation
    rotation.save(update_fields=['participant_snapshot'])
    traffic = info(credential, rotation, now)
    event = record(
        AuditEvent.ROTATION_STEP, credential=credential, account=rotation.source_account,
        summary='All participating clients confirmed the switch or skipped application checks; source secret-fetch observation started.',
    )
    remember(rotation, event, traffic)
    enqueue(event, ApplicationEvent.ROTATION_SOURCE_WAITING, rotation=rotation)
    return traffic


def require_idle(credential, rotation=None, now=None):
    observation = info(credential, rotation, now)
    if not observation or not observation['ready']:
        raise JMSException(
            detail=_('Wait until the source account has no successful JumpServer secret fetches for the configured period.'),
            code='credential_rotation_source_active',
        )
    return observation


def blocker(observation):
    return {
        'application': {'id': '', 'name': 'JumpServer'},
        'client': {'id': '', 'instance_id': 'Secret fetch observation', 'type': 'audit'},
        'reason': 'source_secret_access',
        'source_traffic': observation,
    }


def remember(rotation, event, observation):
    snapshot = rotation.participant_snapshot or {}
    traffic = snapshot.setdefault('source_traffic', {})
    traffic.setdefault('event_observations', {})[str(event.id)] = observation
    rotation.participant_snapshot = snapshot
    rotation.save(update_fields=['participant_snapshot'])


def notify_ready(credential_id, operator_id):
    from accounts.models import ApplicationCredential
    from accounts.notifications import CredentialSourceReadyMsg
    from users.models import User

    user = User.objects.filter(id=operator_id, is_active=True).first()
    if not user or not user.has_perm('accounts.change_applicationcredential'):
        return
    credential = ApplicationCredential.objects.filter(id=credential_id).first()
    if credential and credential.status == credential.Status.ready_for_change:
        CredentialSourceReadyMsg(user, credential).publish(is_async=True)


@transaction.atomic
def record_secret_access(account):
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
