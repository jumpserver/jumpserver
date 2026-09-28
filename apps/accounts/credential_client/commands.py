"""Durable, individually claimed application commands and execution results."""
from datetime import timedelta
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from accounts.const import ApplicationCommandEvent, AuditEvent
from accounts.models import ApplicationCommand, ApplicationCredential, CredentialClientInstance
from common.utils import get_logger
from .audit import record
from .events import configuration_group

SWITCH = ApplicationCommandEvent.ACCOUNT_SWITCH_REQUESTED
RESTART = ApplicationCommandEvent.APPLICATION_RESTART_REQUESTED
TERMINAL = {'success', 'failed', 'timeout'}
logger = get_logger(__name__)


def clients_for(application):
    return CredentialClientInstance.objects.filter(
        application=application, org_id=application.org_id, is_active=True,
        configuration__is_active=True, configuration__org_id=application.org_id,
    ).select_related('configuration').order_by('instance_id', 'id')


def restart_supported(client):
    config = client.configuration
    return client.type == 'sdk' or (
        config.delivery_mode == 'environment' and config.systemd_unit and config.systemd_action == 'restart'
    )


def credentials_for(application):
    return application.application_credentials.filter(
        is_active=True, mode='alternating_rotation',
    ).select_related('active_account__asset').order_by('name', 'id')


def options(application):
    clients = list(clients_for(application))
    credentials = [credential for credential in credentials_for(application)
                   if credential.authorized_applications().filter(id=application.id).exists()]
    return {
        'clients': [{
            'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
            'online': bool(client.date_last_seen and client.date_last_seen >= timezone.now() - timedelta(minutes=2)),
            'restart_supported': bool(restart_supported(client)),
            'credential_ids': [str(value) for value in client.configuration.credentials.values_list('id', flat=True)],
        } for client in clients],
        'credentials': [{
            'id': str(credential.id), 'name': credential.name, 'key': credential.key,
            'revision': credential.revision, 'account_id': str(credential.active_account_id),
            'account': credential.active_account.username, 'asset': credential.active_account.asset.name,
        } for credential in credentials],
    }


def envelope(command):
    return {
        'event_id': str(command.source_event_id), 'command_id': str(command.id),
        'event': command.event, 'occurred_at': command.date_created.isoformat(),
        'expires_at': command.expires_at.isoformat(), **command.payload,
    }


def _expire(command):
    if timezone.now() < command.expires_at:
        return
    changed = False
    for recipient in command.recipients:
        if recipient['status'] not in TERMINAL:
            recipient.update(status='timeout', finished_at=command.expires_at.isoformat())
            changed = True
    if changed:
        command.save(update_fields=['recipients', 'date_updated'])


def detail(command):
    # Calculate deadlines for read-only views, without requiring a scheduler.
    recipients = [dict(item) for item in command.recipients]
    if timezone.now() >= command.expires_at:
        for item in recipients:
            if item['status'] not in TERMINAL:
                item.update(status='timeout', finished_at=command.expires_at.isoformat())
    return {
        **envelope(command), 'operator': command.created_by, 'recipients': recipients,
        'credential': command.source_event.credential, 'account': command.source_event.account,
    }


@transaction.atomic
def send(application, data, operator):
    # Lock the application so disable/delete cannot race the frozen recipient set.
    application = type(application).objects.select_for_update().get(id=application.id)
    if not application.is_active:
        raise ValidationError(_('The application is disabled.'))
    clients = list(clients_for(application).select_for_update(of=('self',)).filter(id__in=data['client_ids']))
    if len(clients) != len(set(data['client_ids'])) or not clients:
        raise ValidationError(_('Select enabled connection instances belonging to this application.'))
    credential = None
    payload = {}
    if data['event'] == SWITCH:
        credential = credentials_for(application).select_for_update(of=('self',)).filter(id=data.get('credential_id')).first()
        if not credential or not credential.authorized_applications().filter(id=application.id).exists():
            raise PermissionDenied(_('Select an authorized account rotation policy for this application.'))
        if credential.status == 'changing_secret':
            raise ValidationError(_('Wait for the account secret change to finish.'))
        if any(not client.configuration.credentials.filter(id=credential.id).exists() for client in clients):
            raise ValidationError(_('The selected connection instances do not all have access to this credential.'))
        payload = {
            'credential_key': credential.key, 'revision': credential.revision,
            'account_id': str(credential.active_account_id), 'credential_mode': credential.mode,
        }
    elif any(not restart_supported(client) for client in clients):
        raise ValidationError(_('The selected Agent must be configured to restart its application service.'))
    audit = record(
        AuditEvent.COMMAND_REQUESTED, application=application, applications=[application],
        credential=credential, account=credential.active_account if credential else None,
        operator=operator, result='pending', summary=data['event'],
    )
    command = ApplicationCommand.objects.create(
        application=application, source_event=audit, event=data['event'], payload=payload,
        created_by=operator, org_id=application.org_id,
        expires_at=timezone.now() + timedelta(minutes=data['timeout_minutes']),
        recipients=[{
            'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
            'configuration_id': str(client.configuration_id), 'status': 'pending',
            'publish_result': 'pending', 'received_at': None, 'started_at': None,
            'finished_at': None, 'error_code': '',
        } for client in clients],
    )
    audit.operation_id = command.id
    audit.save(update_fields=['operation_id'])
    transaction.on_commit(lambda: publish(command.id))
    return command


def publish(command_id):
    command = ApplicationCommand.objects.select_related('application').filter(id=command_id).first()
    if not command or not command.application or not command.application.is_active or timezone.now() >= command.expires_at:
        return
    configurations = {}
    active = {str(client.id) for client in clients_for(command.application)}
    for recipient in command.recipients:
        if recipient['id'] in active:
            configurations.setdefault(recipient['configuration_id'], []).append(recipient['id'])
    for configuration_id, client_ids in configurations.items():
        result = 'published'
        try:
            async_to_sync(get_channel_layer().group_send)(configuration_group(configuration_id), {
                'type': 'credential.event', 'payload': envelope(command), 'recipient_ids': client_ids,
            })
        except Exception:
            result = 'failed'
            logger.warning('Cannot publish application command %s.', command.id)
        with transaction.atomic():
            current = ApplicationCommand.objects.select_for_update().get(id=command.id)
            for recipient in current.recipients:
                if recipient['id'] in client_ids and recipient['status'] == 'pending':
                    recipient['publish_result'] = result
            current.save(update_fields=['recipients', 'date_updated'])


def _valid_client(client):
    if not CredentialClientInstance.objects.filter(
        id=client.id, org_id=client.org_id, application_id=client.application_id,
        configuration_id=client.configuration_id, is_active=True,
        application__is_active=True, application__org_id=client.org_id,
        configuration__is_active=True, configuration__org_id=client.org_id,
    ).exists():
        raise PermissionDenied(_('The client instance is disabled.'))


def _recipient(command, client, validate=True):
    if validate:
        _valid_client(client)
    for recipient in command.recipients:
        if recipient['id'] == str(client.id) and recipient['configuration_id'] == str(client.configuration_id):
            return recipient
    raise NotFound()


def pending(client):
    _valid_client(client)
    commands = ApplicationCommand.objects.filter(
        application_id=client.application_id, org_id=client.org_id, expires_at__gt=timezone.now(),
        recipients__contains=[{'id': str(client.id)}],
    ).order_by('date_created', 'id')
    result = []
    for command in commands:
        recipient = _recipient(command, client, validate=False)
        if recipient['status'] not in TERMINAL:
            result.append({**envelope(command), 'status': recipient['status']})
        if len(result) >= 100:
            break
    return result


@transaction.atomic
def receive(client, event_id):
    try:
        event_id = UUID(str(event_id))
    except (ValueError, TypeError, AttributeError):
        return False
    command = ApplicationCommand.objects.select_for_update().filter(
        source_event_id=event_id, application_id=client.application_id, org_id=client.org_id,
    ).first()
    if not command:
        return False
    recipient = _recipient(command, client)
    _expire(command)
    if recipient['status'] == 'pending':
        recipient.update(status='received', received_at=timezone.now().isoformat(), publish_result='published')
        command.save(update_fields=['recipients', 'date_updated'])
    return True


@transaction.atomic
def report(client, command_id, status, error_code=''):
    command = ApplicationCommand.objects.select_for_update().select_related('application', 'source_event').filter(
        id=command_id, application_id=client.application_id, org_id=client.org_id,
    ).first()
    if not command:
        raise NotFound()
    recipient = _recipient(command, client)
    _expire(command)
    if recipient['status'] in TERMINAL or recipient['status'] == status:
        return {'accepted': False, 'status': recipient['status']}
    now = timezone.now().isoformat()
    if status == 'running':
        if command.event == SWITCH:
            credential = ApplicationCredential.objects.filter(
                key=command.payload['credential_key'], is_active=True,
                applications=client.application, access_configurations=client.configuration,
            ).first()
            if not credential or credential.revision != command.payload['revision'] or str(credential.active_account_id) != command.payload['account_id']:
                recipient.update(status='failed', error_code='superseded', finished_at=now)
                command.save(update_fields=['recipients', 'date_updated'])
                return {'accepted': False, 'status': 'failed'}
        recipient.update(status='running', started_at=now, received_at=recipient['received_at'] or now)
    else:
        if recipient['status'] != 'running':
            raise ValidationError(_('Claim the event before reporting an execution result.'))
        if status == 'success' and command.event == SWITCH:
            from accounts.models import CredentialClientStatus
            if not CredentialClientStatus.objects.filter(
                client=client, binding__credential__key=command.payload['credential_key'],
                applied_revision=command.payload['revision'], applied_account_id=command.payload['account_id'],
            ).exists():
                raise ValidationError(_('Confirm the requested account version before reporting success.'))
        recipient.update(status=status, finished_at=now, error_code=error_code if status == 'failed' else '')
    command.save(update_fields=['recipients', 'date_updated'])
    record(AuditEvent.COMMAND_RESULT, application=client.application, client=client,
           operation_id=command.id, result=status, summary=error_code or command.event)
    return {'accepted': True, 'status': status}
