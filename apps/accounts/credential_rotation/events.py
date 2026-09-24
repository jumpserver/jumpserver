"""Receipt-only progress for credential events; never used to authorize changes."""
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.const import ApplicationEvent, AuditEvent
from accounts.models import (
    ApplicationAudit, ApplicationCredential, ClientAccessConfiguration,
    CredentialClientInstance, CredentialRotationEvent,
)


SUBSCRIPTION_EVENTS = (
    ApplicationEvent.CREDENTIAL_CHANGE_STARTED,
    ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED,
    ApplicationEvent.CREDENTIAL_CHANGE_FAILED,
    ApplicationEvent.CREDENTIAL_UPDATED,
    ApplicationEvent.CREDENTIAL_REVOKED,
    ApplicationEvent.CONFIGURATION_UPDATED,
)


@transaction.atomic
def receive(client_id, org_id, event_id):
    try:
        event_id = UUID(str(event_id))
    except (ValueError, TypeError, AttributeError):
        return False
    client = CredentialClientInstance.objects.filter(
        id=client_id, org_id=org_id, is_active=True,
        application__is_active=True, application__org_id=org_id,
        configuration__is_active=True, configuration__org_id=org_id,
    ).first()
    if not client:
        return False
    event = CredentialRotationEvent.objects.select_for_update().filter(
        source_event_id=event_id, org_id=org_id,
    ).first()
    if not event:
        return False
    for recipient in event.recipients:
        if (
            recipient['id'] != str(client.id)
            or recipient['application']['id'] != str(client.application_id)
            or recipient['configuration']['id'] != str(client.configuration_id)
        ):
            continue
        if recipient['received_at'] is None:
            recipient['received_at'] = timezone.now().isoformat()
            recipient['supports_receipts'] = True
            # A client can reply before group_send's publication result is saved.
            recipient['publish_result'] = 'published'
            event.save(update_fields=['recipients', 'date_updated'])
        return True
    return False


def timeline(credential, rotation_id=None):
    if credential.mode == ApplicationCredential.Mode.subscription:
        return _subscription_timeline(credential)
    rotations = credential.rotation_records.all()
    rotation = rotations.filter(id=rotation_id).first() if rotation_id else rotations.first()
    if not rotation:
        return {'rotation_id': None, 'status': None, 'events': [], 'instances': []}
    events = list(rotation.events.all())
    instances = {}
    for participant in (rotation.participant_snapshot or {}).get('participants', []):
        instances[participant['client']['id']] = {
            **participant['client'],
            'application': participant['application'],
            'configuration': participant['configuration'],
            'supports_receipts': participant['client'].get('supports_receipts', False),
            'receipts': [],
        }
    return _build_timeline(events, instances, rotation.org_id, rotation.id, rotation.status)


def subscription_events(credential):
    configurations = ClientAccessConfiguration.objects.filter(
        credentials=credential,
    )
    applications = credential.applications.values('id')
    source_events = ApplicationAudit.objects.filter(
        Q(credential_id=credential.id) |
        (
            Q(event=AuditEvent.CONFIGURATION_UPDATED) &
            (
                Q(configuration_id__in=configurations.values('id')) |
                Q(service_id__in=applications) |
                Q(application_relations__application_id__in=applications)
            )
        ),
        org_id=credential.org_id,
    ).values('id').distinct()
    return CredentialRotationEvent.objects.filter(
        rotation__isnull=True, source_event_id__in=source_events,
        event__in=SUBSCRIPTION_EVENTS, org_id=credential.org_id,
    )


def _subscription_timeline(credential):
    configurations = ClientAccessConfiguration.objects.filter(credentials=credential)
    events = list(subscription_events(credential).order_by('published_at', 'id'))
    clients = CredentialClientInstance.objects.filter(
        configuration__in=configurations,
        application__credential_bindings__credential=credential,
        org_id=credential.org_id,
    ).select_related('application', 'configuration').distinct()
    instances = {
        str(client.id): {
            'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
            'application': {'id': str(client.application_id), 'name': client.application.name},
            'configuration': {'id': str(client.configuration_id), 'name': client.configuration.name},
            'supports_receipts': client.event_receipts_supported, 'receipts': [],
        }
        for client in clients
    }
    return _build_timeline(events, instances, credential.org_id)


def _build_timeline(events, instances, org_id, rotation_id=None, status=None):
    for event in events:
        for recipient in event.recipients:
            instance = instances.setdefault(recipient['id'], {
                key: recipient[key] for key in (
                    'id', 'instance_id', 'type', 'application', 'configuration',
                    'supports_receipts',
                )
            })
            instance['supports_receipts'] = recipient['supports_receipts']
            instance.setdefault('receipts', []).append({
                'event_id': str(event.source_event_id),
                'received_at': recipient['received_at'],
                'publish_result': recipient['publish_result'],
            })
    live_clients = {
        str(client.id): client for client in CredentialClientInstance.objects.filter(
            id__in=instances, org_id=org_id,
        ).select_related('application', 'configuration')
    }
    for instance in instances.values():
        client = live_clients.get(instance['id'])
        instance['is_active'] = bool(client and client.is_valid)
        instance['online'] = bool(instance['is_active'] and client.online)
        if client:
            instance['supports_receipts'] = client.event_receipts_supported
        receipts = instance['receipts']
        received = [item for item in receipts if item['received_at']]
        instance['event_count'] = len(receipts)
        instance['received_count'] = len(received)
        instance['latest_event_id'] = received[-1]['event_id'] if received else None
        latest_index = receipts.index(received[-1]) if received else -1
        instance['missing_count'] = sum(
            item['received_at'] is None for item in receipts[:latest_index]
        ) if received else 0
    return {
        'rotation_id': str(rotation_id) if rotation_id else None, 'status': status,
        'events': [{
            'id': str(event.source_event_id), 'event': event.event,
            'sequence': sequence, 'published_at': event.published_at.isoformat(),
            'revision': event.revision,
        } for sequence, event in enumerate(events, start=1)],
        'instances': sorted(instances.values(), key=lambda item: (
            item['application']['name'], item['configuration']['name'], item['instance_id'],
        )),
    }
