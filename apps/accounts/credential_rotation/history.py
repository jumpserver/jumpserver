"""Read-only, paginated client history across credential rotations/subscriptions."""
from accounts.models import ApplicationCredential, CredentialClientInstance, CredentialRotationEvent
from .events import subscription_events


IDENTITY_FIELDS = ('id', 'instance_id', 'type', 'application', 'configuration', 'supports_receipts')


def events_for(credential):
    if credential.mode == ApplicationCredential.Mode.subscription:
        events = subscription_events(credential)
    else:
        events = CredentialRotationEvent.objects.filter(
            rotation__credential=credential, org_id=credential.org_id,
        )
    return events.order_by('-published_at', '-id')


def event_data(event, recipient):
    return {
        'id': str(event.source_event_id), 'event': event.event,
        'published_at': event.published_at.isoformat(), 'revision': event.revision,
        'rotation_id': str(event.rotation_id) if event.rotation_id else None,
        'received_at': recipient['received_at'], 'publish_result': recipient['publish_result'],
    }


def client_data(client):
    return {
        'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
        'application': {'id': str(client.application_id), 'name': client.application.name},
        'configuration': {'id': str(client.configuration_id), 'name': client.configuration.name},
        'supports_receipts': client.event_receipts_supported,
        'is_active': client.is_valid, 'online': bool(client.is_valid and client.online),
    }


def directory(credential, search='', client_type='', state=''):
    rows = {}
    # ponytail: scan stored recipient snapshots for historical/deleted identities;
    # normalize recipients into indexed rows if event retention makes this expensive.
    for event in events_for(credential).iterator(chunk_size=100):
        for recipient in event.recipients:
            row = rows.setdefault(recipient['id'], {
                **{key: recipient[key] for key in IDENTITY_FIELDS},
                'latest_event': event_data(event, recipient), 'latest_received_event': None,
                'is_active': False, 'online': False,
            })
            received = row['latest_received_event']
            if recipient['received_at'] and (
                not received or recipient['received_at'] > received['received_at']
            ):
                row['latest_received_event'] = event_data(event, recipient)
    live = CredentialClientInstance.objects.filter(
        configuration__credentials=credential, application__credential_bindings__credential=credential,
        org_id=credential.org_id,
    ).select_related('application', 'configuration').distinct()
    # Keep removed bindings/instances in history, but show their current state when still present.
    historical = CredentialClientInstance.objects.filter(
        id__in=rows, org_id=credential.org_id,
    ).select_related('application', 'configuration')
    for client in list(historical) + list(live):
        row = rows.setdefault(str(client.id), {'latest_event': None, 'latest_received_event': None})
        row.update(client_data(client))
    search = search.casefold().strip()
    result = []
    for row in rows.values():
        if search and not any(search in value.casefold() for value in (
            row['instance_id'], row['application']['name'], row['configuration']['name'],
        )):
            continue
        if client_type and row['type'] != client_type:
            continue
        if state == 'online' and not row['online']:
            continue
        if state == 'offline' and (row['online'] or not row['is_active']):
            continue
        if state == 'inactive' and row['is_active']:
            continue
        result.append(row)
    return sorted(result, key=lambda row: (
        row['application']['name'], row['configuration']['name'], row['instance_id'], row['id'],
    ))


def client_history(credential, client_id, limit, offset):
    client_id = str(client_id)
    events = events_for(credential).filter(recipients__contains=[{'id': client_id}])

    def serialize(event):
        recipient = next(row for row in event.recipients if row['id'] == client_id)
        return event_data(event, recipient)

    latest = events.first()
    clients = CredentialClientInstance.objects.filter(id=client_id, org_id=credential.org_id)
    if not latest:
        clients = clients.filter(
            configuration__credentials=credential, application__credential_bindings__credential=credential,
        )
    client = clients.select_related('application', 'configuration').first()
    if not latest and not client:
        from rest_framework.exceptions import NotFound
        raise NotFound()
    if client:
        identity = client_data(client)
    else:
        recipient = next(row for row in latest.recipients if row['id'] == client_id)
        identity = {**{key: recipient[key] for key in IDENTITY_FIELDS}, 'is_active': False, 'online': False}
    received = None
    for event in events.exclude(recipients__contains=[{'id': client_id, 'received_at': None}]).iterator(chunk_size=100):
        item = serialize(event)
        if item['received_at'] and (not received or item['received_at'] > received['received_at']):
            received = item
    return {
        'client': identity, 'count': events.count(),
        'latest_event': serialize(latest) if latest else None, 'latest_received_event': received,
        'results': [serialize(event) for event in events[offset:offset + limit]],
    }
