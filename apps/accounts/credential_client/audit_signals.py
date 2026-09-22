"""Observe committed domain changes using the project's model signal entry points."""
from django.db import transaction
from django.db.models import F
from django.db.models.signals import pre_save, post_save, pre_delete, m2m_changed
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from simple_history.signals import post_create_historical_record

from accounts.const import AuditEvent, ApplicationEvent, ChangeSecretRecordStatusChoice
from accounts.models import (
    ApplicationCredential, ClientAccessConfiguration, CredentialClientInstance,
    CredentialClientStatus, IntegrationApplication, ChangeSecretRecord, Account,
    CredentialRotationRecord, ChangeSecretAutomation, AutomationExecution,
)
from assets.models import BaseAutomation, AutomationExecution as AssetAutomationExecution
from .audit import record
from .events import enqueue


MODEL_AUDIT_FIELDS = {
    ApplicationCredential: (
        'name', 'mode', 'account_id', 'alternate_account_id', 'active_account_id',
        'status', 'revision', 'is_active',
    ),
    ClientAccessConfiguration: (
        'name', 'is_active', 'app_user', 'install_path', 'delivery_mode',
        'systemd_unit', 'systemd_action',
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
        )
        enqueue(event, application_event)
    if instance.status == ChangeSecretRecordStatusChoice.success:
        publish_subscription_credentials_for_account(instance.account)


def publish_subscription_credentials_for_account(account, revision=None):
    account = Account.objects.get(pk=account.pk)
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
    if event.event == AuditEvent.CREDENTIAL_PUBLISHED:
        enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED)
    elif event.event == AuditEvent.ROTATION_STEP:
        if instance.status in (
            ApplicationCredential.Status.change_failed,
            ApplicationCredential.Status.recovery_required,
        ):
            enqueue(event, ApplicationEvent.ROTATION_FAILED)
    elif isinstance(instance, ClientAccessConfiguration):
        enqueue(event, ApplicationEvent.CONFIGURATION_UPDATED)
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
            states = list(CredentialClientStatus.objects.select_related(
                'binding__application', 'client__configuration', 'applied_account',
            ).filter(
                client__configuration=instance,
                binding__credential=credential,
            ))
            if credential.status != ApplicationCredential.Status.idle:
                from accounts.credential_rotation.participants import exclude
                exclude(credential, states, reason)
            event = record(
                AuditEvent.AUTHORIZATION_REVOKED,
                credential=credential,
                configuration=instance,
                summary=reason,
            )
            enqueue(event, ApplicationEvent.CREDENTIAL_REVOKED)
        CredentialClientStatus.objects.filter(
            client__configuration=instance,
            binding__credential_id__in=[credential.id for credential in credentials],
        ).delete()
    elif action == 'post_add':
        for credential in instance.credentials.filter(pk__in=pk_set):
            event = record(AuditEvent.AUTHORIZATION_GRANTED, credential=credential, configuration=instance)
            enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED)


for model in MODEL_AUDIT_FIELDS:
    pre_save.connect(before_save, sender=model)
    post_save.connect(after_save, sender=model)
    if model not in (Account, ChangeSecretRecord):
        pre_delete.connect(before_delete, sender=model)
m2m_changed.connect(credentials_changed, sender=ClientAccessConfiguration.credentials.through)
post_create_historical_record.connect(publish_subscription_credentials, sender=Account.history.model)
for model in (BaseAutomation, ChangeSecretAutomation, AutomationExecution, AssetAutomationExecution):
    pre_delete.connect(protect_rotation_execution, sender=model)
