"""Observe committed domain changes using the project's model signal entry points."""
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, m2m_changed
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from accounts.const import AuditEvent, ApplicationEvent, ChangeSecretRecordStatusChoice
from accounts.models import (
    ApplicationCredential, ClientAccessConfiguration, CredentialClientInstance,
    CredentialClientStatus, IntegrationApplication, ChangeSecretRecord, Account,
)
from .audit import record
from .events import enqueue


MODEL_AUDIT_FIELDS = {
    ApplicationCredential: (
        'name', 'type', 'primary_account_id', 'backup_account_id', 'status', 'revision', 'is_active',
    ),
    ClientAccessConfiguration: (
        'name', 'is_active', 'notification_enabled', 'notification_url', 'app_user', 'install_path',
    ),
    CredentialClientInstance: ('is_active',),
    IntegrationApplication: ('name', 'is_active', 'accounts', 'ip_group'),
    ChangeSecretRecord: ('status',),
    Account: ('version',),
}


def snapshot(instance):
    result = {}
    for name in MODEL_AUDIT_FIELDS[type(instance)]:
        value = getattr(instance, name)
        if name == 'accounts':
            value = value.value
        result[name] = value if isinstance(value, (str, int, bool, dict, list, type(None))) else str(value)
    return result


def before_save(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw:
        instance._application_audit_before = None
        return
    if sender is not Account and update_fields and not set(update_fields).intersection(MODEL_AUDIT_FIELDS[sender]):
        instance._application_audit_before = None
        return
    previous = sender.objects.filter(pk=instance.pk).first()
    instance._application_audit_before = snapshot(previous) if previous else {}


def get_audit_context(instance):
    if isinstance(instance, ApplicationCredential):
        return {'credential': instance}
    if isinstance(instance, ClientAccessConfiguration):
        return {'configuration': instance}
    if isinstance(instance, CredentialClientInstance):
        return {'client': instance}
    return {'application': instance}


def after_save(sender, instance, created=False, raw=False, **kwargs):
    before = getattr(instance, '_application_audit_before', None)
    if raw or before is None:
        return
    after = snapshot(instance)
    changes = [{'field': key, 'before': before.get(key), 'after': value}
               for key, value in after.items() if value != before.get(key)]
    if not changes:
        return
    if sender is ChangeSecretRecord:
        return record_secret_change(instance)
    if sender is Account:
        if not created:
            publish_fixed_credentials(instance)
        return

    event_name = get_audit_event(instance, created, before, after)
    event = record(event_name, **get_audit_context(instance), changes=changes)
    notify_model_change(instance, event, changes)


def record_secret_change(instance):
    terminal_statuses = (ChangeSecretRecordStatusChoice.success, ChangeSecretRecordStatusChoice.failed)
    if instance.status not in terminal_statuses or not instance.account_id:
        return
    credentials = ApplicationCredential.objects.filter(primary_account_id=instance.account_id).exclude(
        status=ApplicationCredential.Status.idle,
    )
    for credential in credentials:
        event = record(AuditEvent.SECRET_CHANGE_FINISHED, credential=credential, result=instance.status)
        if instance.status == ChangeSecretRecordStatusChoice.failed:
            enqueue(event, ApplicationEvent.ROTATION_FAILED)


def publish_fixed_credentials(account):
    credentials = ApplicationCredential.objects.filter(primary_account=account, type=ApplicationCredential.Type.fixed)
    for credential in credentials:
        event = record(AuditEvent.CREDENTIAL_PUBLISHED, credential=credential)
        enqueue(event, ApplicationEvent.CREDENTIAL_PUBLISHED)


def get_audit_event(instance, created, before, after):
    if isinstance(instance, CredentialClientInstance):
        if created:
            return AuditEvent.CLIENT_REGISTERED
        return AuditEvent.CLIENT_ENABLED if instance.is_active else AuditEvent.CLIENT_DISABLED
    if isinstance(instance, ApplicationCredential) and not created:
        if before.get('revision') != after['revision']:
            return AuditEvent.CREDENTIAL_PUBLISHED
        if before.get('status') != after['status']:
            return AuditEvent.ROTATION_STEP
    return AuditEvent.CONFIGURATION_CREATED if created else AuditEvent.CONFIGURATION_UPDATED


def notify_model_change(instance, event, changes):
    if event.event == AuditEvent.CREDENTIAL_PUBLISHED:
        enqueue(event, ApplicationEvent.CREDENTIAL_PUBLISHED)
    elif event.event == AuditEvent.ROTATION_STEP:
        if (
            instance.status == ApplicationCredential.Status.changing_secret
            and instance.rotation_mode == ApplicationCredential.RotationMode.single
        ):
            enqueue(event, ApplicationEvent.CREDENTIAL_UNAVAILABLE)
    elif isinstance(instance, IntegrationApplication) and any(change['field'] == 'accounts' for change in changes):
        notify_revoked_credentials(instance)


def notify_revoked_credentials(application):
    allowed_accounts = set(application.get_accounts().values_list('id', flat=True))
    with transaction.atomic():
        credentials = application.application_credentials.select_for_update(
            of=('self',)
        ).order_by('key')
        for credential in credentials:
            required_accounts = {credential.primary_account_id, credential.backup_account_id} - {None}
            if required_accounts.issubset(allowed_accounts):
                continue
            event = record(AuditEvent.AUTHORIZATION_REVOKED, credential=credential, application=application)
            clients = application.credential_clients.filter(configuration__credentials=credential)
            enqueue(event, ApplicationEvent.ACCESS_REVOKED, clients)
            CredentialClientStatus.objects.filter(
                binding__credential=credential,
                client__application=application,
            ).delete()


def before_delete(sender, instance, **kwargs):
    record(AuditEvent.CONFIGURATION_DELETED, **get_audit_context(instance))


def credentials_changed(sender, instance, action, reverse, pk_set, **kwargs):
    if reverse:
        return  # API mutates configuration.credentials, never the reverse manager.
    if action in ('pre_remove', 'pre_clear'):
        credentials = instance.credentials.select_for_update(of=('self',)).order_by('key')
        if pk_set is not None:
            credentials = credentials.filter(pk__in=pk_set)
        credentials = list(credentials)
        reason = getattr(instance, '_credential_removal_reason', '').strip()
        rotating = any(
            credential.status != ApplicationCredential.Status.idle
            for credential in credentials
        )
        if rotating and not reason:
            raise ValidationError(_('Explain why the rotating credential should stop participating.'))
        for credential in credentials:
            event = record(
                AuditEvent.AUTHORIZATION_REVOKED,
                credential=credential,
                configuration=instance,
                summary=reason,
            )
            enqueue(event, ApplicationEvent.ACCESS_REVOKED, instance.instances.all())
        CredentialClientStatus.objects.filter(
            client__configuration=instance,
            binding__credential_id__in=[credential.id for credential in credentials],
        ).delete()
    elif action == 'post_add':
        for credential in instance.credentials.filter(pk__in=pk_set):
            event = record(AuditEvent.AUTHORIZATION_GRANTED, credential=credential, configuration=instance)
            enqueue(event, ApplicationEvent.CREDENTIAL_PUBLISHED, instance.instances.all())


for model in MODEL_AUDIT_FIELDS:
    pre_save.connect(before_save, sender=model)
    post_save.connect(after_save, sender=model)
    if model not in (Account, ChangeSecretRecord):
        pre_delete.connect(before_delete, sender=model)
m2m_changed.connect(credentials_changed, sender=ClientAccessConfiguration.credentials.through)
