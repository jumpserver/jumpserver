"""Observe successful JumpServer secret fetches for the account being replaced."""
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from common.exceptions import JMSException


def info(credential, rotation=None, now=None):
    rotation = rotation or credential.rotation_records.first()
    if not rotation or rotation.date_finished or rotation.status != 'running':
        return None
    observation = (rotation.participant_snapshot or {}).get('source_traffic', {})
    started_at = parse_datetime(observation['started_at']) if observation.get('started_at') else credential.date_rotation_started
    if not started_at:
        return None
    days = observation.get('no_traffic_days', credential.source_no_traffic_days)
    last_access = Account.objects.filter(id=rotation.source_account_id).values_list(
        'date_last_secret_access', flat=True,
    ).get()
    idle_since = max(started_at, last_access) if last_access else started_at
    eligible_at = idle_since + timedelta(days=days)
    now = now or timezone.now()
    return {
        'source_account_id': str(rotation.source_account_id),
        'started_at': started_at.isoformat(),
        'no_traffic_days': days,
        'last_secret_access': last_access.isoformat() if last_access and last_access >= started_at else None,
        'idle_since': idle_since.isoformat(),
        'eligible_at': eligible_at.isoformat(),
        'remaining_seconds': max(0, (eligible_at - now).total_seconds()),
        'ready': now >= eligible_at,
    }


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
