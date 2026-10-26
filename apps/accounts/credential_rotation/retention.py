"""Expire whole, finished cycles before removing their dependent audit history."""
from django.db import transaction
from django.db.models import Exists, Max, OuterRef, Q
from django.db.models.functions import Coalesce

from accounts.const import ApplicationEvent, AuditEvent
from accounts.models import (
    ApplicationAudit, ApplicationCredential, ApplicationEventDelivery, ChangeSecretRecord,
    CredentialRotationEvent, CredentialRotationRecord,
)


def clean_cycles(expired_at):
    counts = {}

    def delete(queryset):
        _, deleted = queryset.delete()
        for label, count in deleted.items():
            counts[label] = counts.get(label, 0) + count

    # Writers acquire the policy lock before the rotation lock. Use that same
    # order, and recheck eligibility after locking to avoid racing a retry.
    rotations = CredentialRotationRecord.objects.filter(
        status__in=('success', 'cancelled'), date_finished__lt=expired_at,
    ).order_by('id').values_list('id', 'credential_id')
    for rotation_id, credential_id in rotations.iterator(chunk_size=100):
        with transaction.atomic():
            credential = ApplicationCredential.objects.select_for_update().filter(id=credential_id).first()
            rotation = CredentialRotationRecord.objects.select_for_update().filter(
                id=rotation_id, status__in=('success', 'cancelled'), date_finished__lt=expired_at,
            ).first()
            if not credential or not rotation or (
                credential.change_execution_id and credential.change_execution_id == rotation.change_execution_id
            ):
                continue
            if rotation.events.filter(published_at__gte=expired_at).exists():
                continue
            if ApplicationEventDelivery.objects.filter(
                event__rotation_id=rotation.id, status='pending', org_id=rotation.org_id,
            ).exists():
                continue
            delete(CredentialRotationRecord.objects.filter(id=rotation.id))

    # A subscription operation can contain multiple accounts and events. Expire
    # the group only once its last event is old; never split it at the cutoff.
    events = CredentialRotationEvent.objects.filter(rotation__isnull=True).annotate(
        cycle_key=Coalesce('cycle_id', 'source_event_id'),
    )
    groups = events.order_by().values('org_id', 'cycle_key').annotate(
        last_event=Max('published_at'),
    ).filter(last_event__lt=expired_at).order_by('org_id', 'cycle_key')
    for group in groups.iterator(chunk_size=100):
        with transaction.atomic():
            cycle = events.filter(org_id=group['org_id'], cycle_key=group['cycle_key'])
            rows = list(cycle.select_for_update().order_by('published_at', 'id'))
            if not rows or any(row.published_at >= expired_at for row in rows):
                continue
            codes = [row.event for row in rows]
            # Keep incomplete and failed operations available for investigation.
            if ApplicationEvent.CREDENTIAL_CHANGE_STARTED in codes and codes[-1] not in (
                ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED, ApplicationEvent.CREDENTIAL_UPDATED,
            ):
                continue
            if ApplicationEvent.CREDENTIAL_CHANGE_FAILED in codes:
                continue
            if ChangeSecretRecord.objects.filter(
                id=group['cycle_key'], status__in=('pending', 'running'), execution__org_id=group['org_id'],
            ).exists():
                continue
            source_ids = [row.source_event_id for row in rows]
            if ApplicationEventDelivery.objects.filter(event_id__in=source_ids, status='pending').exists():
                continue
            # Account-switch grants can still be awaiting application results.
            switching = ApplicationAudit.objects.filter(
                id__in=source_ids,
                credential_id__in=ApplicationCredential.objects.filter(mode='alternating_rotation').values('id'),
            ).exists()
            if switching and any(
                row.event == ApplicationEvent.CREDENTIAL_UPDATED
                and any(recipient.get('status') != 'success' for recipient in row.recipients)
                for row in rows
            ):
                continue
            delete(CredentialRotationEvent.objects.filter(id__in=[row.id for row in rows]))
    return counts


def protected_audits():
    """Source audits and confirmations must survive as long as their cycles."""
    events = CredentialRotationEvent.objects.all()
    sources = ApplicationAudit.objects.filter(id__in=events.values('source_event_id'))
    confirmations = sources.filter(
        credential_id=OuterRef('credential_id'), revision=OuterRef('revision'), org_id=OuterRef('org_id'),
    )
    return ApplicationAudit.objects.alias(
        retained_confirmation=Exists(confirmations),
    ).filter(
        Q(id__in=events.values('source_event_id'))
        | Q(rotation_id__in=CredentialRotationRecord.objects.values('id'))
        | Q(operation_id__in=events.exclude(cycle_id=None).values('cycle_id'))
        | Q(event=AuditEvent.CREDENTIAL_CONFIRMED, retained_confirmation=True)
    )
