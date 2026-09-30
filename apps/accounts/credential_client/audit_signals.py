"""Observe committed domain changes using the project's model signal entry points."""
from uuid import uuid4

from django.db import transaction
from django.db.models import F, Q
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from simple_history.signals import post_create_historical_record

from accounts.const import AuditEvent, ApplicationEvent, ChangeSecretRecordStatusChoice
from accounts.models import (
    ApplicationCredential, CredentialClientInstance,
    CredentialClientStatus, IntegrationApplication, ChangeSecretRecord, Account,
    CredentialRotationRecord, ChangeSecretAutomation, AutomationExecution,
    CredentialApplicationBinding,
)
from assets.models import BaseAutomation, AutomationExecution as AssetAutomationExecution
from .audit import record
from .events import enqueue


MODEL_AUDIT_FIELDS = {
    ApplicationCredential: (
        'name', 'mode', 'account_id', 'alternate_account_id', 'active_account_id',
        'status', 'revision', 'is_active',
    ),
    CredentialClientInstance: ('is_active',),
    IntegrationApplication: ('name', 'is_active', 'accounts', 'ip_group'),
    ChangeSecretRecord: ('status',),
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
        return record_secret_change(instance, before, after)

    event_name = get_audit_event(instance, created, before, after)
    event = record(
        event_name, **get_audit_context(instance), changes=changes,
        summary=getattr(instance, '_application_audit_summary', ''),
    )
    notify_model_change(instance, event, changes)


def record_secret_change(instance, before, after):
    if not instance.account_id or before.get('status') == after.get('status'):
        return
    if CredentialRotationRecord.objects.filter(change_execution_id=instance.execution_id).exists():
        return
    credentials, applications = subscription_targets(instance.account)
    if instance.status in ('pending', 'running'):
        if before.get('status') in ('pending', 'running'):
            return  # Queueing and execution are the same change-start stage.
        audit_event = AuditEvent.SECRET_CHANGE_STARTED
        application_event = ApplicationEvent.CREDENTIAL_CHANGE_STARTED
        result = 'pending'
    elif instance.status == ChangeSecretRecordStatusChoice.success:
        audit_event = AuditEvent.SECRET_CHANGE_COMPLETED
        application_event = ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED
        result = 'success'
    elif instance.status == ChangeSecretRecordStatusChoice.failed:
        audit_event = AuditEvent.SECRET_CHANGE_FAILED
        application_event = ApplicationEvent.CREDENTIAL_CHANGE_FAILED
        result = 'failed'
    else:
        return
    for credential in credentials:
        targets = list(applications.filter(application_credentials=credential))
        event = record(
            audit_event, credential=credential, account=instance.account,
            applications=targets, result=result,
            credential_key=credential.account_key(instance.account_id),
            revision=instance.account.version,
            operation_id=instance.id,
        )
        enqueue(event, application_event)
    if instance.status == ChangeSecretRecordStatusChoice.success:
        publish_subscription_credentials_for_account(instance.account, operation_id=instance.id)


def publish_subscription_credentials_for_account(account, revision=None, operation_id=None):
    account = Account.objects.get(pk=account.pk)
    operation_id = operation_id or uuid4()
    revision = account.version if revision is None else revision
    credentials, applications = subscription_targets(account, lock=True)
    for credential in credentials:
        ApplicationCredential.objects.filter(pk=credential.pk).update(
            revision=F('revision') + 1, date_updated=timezone.now(),
        )
        credential.refresh_from_db(fields=['revision', 'date_updated'])
        targets = list(applications.filter(application_credentials=credential))
        event = record(
            AuditEvent.CREDENTIAL_PUBLISHED, credential=credential, account=account,
            applications=targets, credential_key=credential.account_key(account.id),
            revision=revision,
            operation_id=operation_id,
        )
        enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED)


def subscription_targets(account, lock=False):
    applications = IntegrationApplication.objects.filter(
        IntegrationApplication.accounts.get_filter_q(account), is_active=True,
    ).distinct()
    credentials = ApplicationCredential.objects.filter(
        applications__in=applications,
        mode=ApplicationCredential.Mode.subscription,
        is_active=True,
    ).filter(
        Q(subscription_all_authorized=True) | Q(subscription_accounts=account),
    ).distinct().order_by('key')
    if lock:
        ids = credentials.values('id')
        credentials = ApplicationCredential.objects.select_for_update(
            of=('self',)
        ).filter(id__in=ids).order_by('key')
    return credentials, applications


def publish_subscription_credentials(sender, instance, history_instance, **kwargs):
    if history_instance.history_type != '~':
        return
    # JumpServer change records publish only after the completed lifecycle event.
    managed_change = ChangeSecretRecord.objects.filter(account=instance).exclude(
        status=ChangeSecretRecordStatusChoice.success,
    ).order_by('-date_created').first()
    if managed_change and managed_change.new_secret == instance.secret:
        return
    publish_subscription_credentials_for_account(instance, history_instance.version)


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
    rotation = None
    if (
        isinstance(instance, ApplicationCredential)
        and instance.mode == ApplicationCredential.Mode.alternating_rotation
        and instance.status != ApplicationCredential.Status.idle
    ):
        rotation = instance.rotation_records.filter(
            status__in=('running', 'preparing'), date_finished__isnull=True,
        ).first()
    if event.event == AuditEvent.CREDENTIAL_PUBLISHED:
        enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED, rotation=rotation)
    elif event.event == AuditEvent.ROTATION_STEP:
        if instance.status in (
            ApplicationCredential.Status.change_failed,
            ApplicationCredential.Status.recovery_required,
        ):
            enqueue(event, ApplicationEvent.ROTATION_FAILED, rotation=rotation)
    elif isinstance(instance, ApplicationCredential) and any(change['field'] == 'is_active' for change in changes):
        enqueue(event, ApplicationEvent.CONFIGURATION_UPDATED if instance.is_active else ApplicationEvent.CREDENTIAL_REVOKED)
    elif isinstance(instance, IntegrationApplication) and any(change['field'] == 'accounts' for change in changes):
        enqueue(event, ApplicationEvent.CONFIGURATION_UPDATED)
        notify_revoked_credentials(instance)


def notify_revoked_credentials(application):
    allowed_accounts = set(application.get_accounts().values_list('id', flat=True))
    with transaction.atomic():
        credentials = application.application_credentials.select_for_update(
            of=('self',)
        ).order_by('key')
        for credential in credentials:
            required_accounts = {credential.account_id, credential.alternate_account_id} - {None}
            if required_accounts.issubset(allowed_accounts):
                continue
            event = record(AuditEvent.AUTHORIZATION_REVOKED, credential=credential, application=application)
            enqueue(event, ApplicationEvent.CREDENTIAL_REVOKED)
            CredentialClientStatus.objects.filter(
                binding__credential=credential,
                client__application=application,
            ).delete()


def before_delete(sender, instance, **kwargs):
    if isinstance(instance, ApplicationCredential) and instance.rotation_records.filter(
        change_automation__isnull=False,
    ).exists():
        raise ValidationError(_('Delete the linked rotation tasks before deleting this credential.'))
    record(AuditEvent.CONFIGURATION_DELETED, **get_audit_context(instance))


def protect_rotation_execution(sender, instance, **kwargs):
    if sender in (BaseAutomation, ChangeSecretAutomation):
        rotations = CredentialRotationRecord.objects.filter(change_automation_id=instance.pk)
    else:
        rotations = CredentialRotationRecord.objects.filter(change_execution_id=instance.pk)
    for rotation in rotations.select_related('credential'):
        if rotation.status == 'running' and not rotation.date_finished:
            # Use the same credential lock as create/execute/cancel.
            ApplicationCredential.objects.select_for_update().get(pk=rotation.credential_id)
            rotation.refresh_from_db()
            if rotation.status == 'running' and not rotation.date_finished:
                raise ValidationError(_('An active rotation task or execution cannot be deleted.'))


def application_binding_changed(sender, instance, created=False, signal=None, **kwargs):
    from .access import publish_application_scope
    from accounts.credential_rotation.participants import enroll_client
    application = IntegrationApplication.objects.filter(pk=instance.application_id).first()
    if not application or (signal is post_save and not created):
        return
    for client in application.credential_clients.filter(is_active=True):
        enroll_client(client)
    publish_application_scope(application)
    credential = ApplicationCredential.objects.filter(pk=instance.credential_id).first()
    if not credential:
        return
    if signal is post_delete:
        event_name, event_code = AuditEvent.AUTHORIZATION_REVOKED, ApplicationEvent.CREDENTIAL_REVOKED
    else:
        event_name, event_code = AuditEvent.AUTHORIZATION_GRANTED, ApplicationEvent.CREDENTIAL_UPDATED
    event = record(event_name, credential=credential, application=application)
    enqueue(event, event_code)


def before_application_binding_deleted(sender, instance, **kwargs):
    from accounts.credential_rotation.participants import exclude
    credential = ApplicationCredential.objects.filter(pk=instance.credential_id).first()
    if not credential:
        return
    states = list(instance.client_statuses.select_related(
        'client', 'binding__application', 'applied_account',
    ))
    exclude(credential, states, str(_('Application policy binding removed.')))


for model in MODEL_AUDIT_FIELDS:
    pre_save.connect(before_save, sender=model)
    post_save.connect(after_save, sender=model)
    if model not in (Account, ChangeSecretRecord):
        pre_delete.connect(before_delete, sender=model)
post_save.connect(application_binding_changed, sender=CredentialApplicationBinding)
pre_delete.connect(before_application_binding_deleted, sender=CredentialApplicationBinding)
post_delete.connect(application_binding_changed, sender=CredentialApplicationBinding)
post_create_historical_record.connect(publish_subscription_credentials, sender=Account.history.model)
for model in (BaseAutomation, ChangeSecretAutomation, AutomationExecution, AssetAutomationExecution):
    pre_delete.connect(protect_rotation_execution, sender=model)
