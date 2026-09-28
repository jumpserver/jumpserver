"""Start another policy cycle without simulating password-change results."""
from uuid import uuid4

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from accounts.const import ApplicationEvent, AuditEvent, AuditSource
from accounts.credential_client.audit import record
from accounts.credential_client.events import enqueue
from accounts.models import Account, ApplicationCredential, ChangeSecretRecord
from common.exceptions import JMSException


@transaction.atomic
def start(credential_id, operator='', operator_id=None):
    credential = ApplicationCredential.objects.select_for_update().get(pk=credential_id)
    if not credential.is_active or credential.status != credential.Status.idle:
        raise JMSException(_('Only active, idle policies can start a new cycle.'))
    if credential.mode == credential.Mode.alternating_rotation:
        from .manager import CredentialRotationManager
        credential = CredentialRotationManager(credential.id).prepare(operator, operator_id)
        return credential, credential.rotation_records.first().id

    applications = list(credential.applications.filter(is_active=True, org_id=credential.org_id))
    allowed = {}
    for application in applications:
        ids = set(application.get_accounts().filter(org_id=credential.org_id).values_list('id', flat=True))
        allowed[application.id] = ids
    account_ids = set().union(*allowed.values()) if allowed else set()
    accounts = Account.objects.filter(id__in=account_ids, org_id=credential.org_id)
    if not credential.subscription_all_authorized:
        accounts = accounts.filter(subscribed_application_credentials=credential)
    accounts = list(accounts.distinct().order_by('id'))
    if not accounts:
        raise JMSException(_('No authorized subscription accounts are available for notification.'))
    if ChangeSecretRecord.objects.filter(account__in=accounts, status__in=('pending', 'running')).exists():
        raise JMSException(_('Wait for the current account secret changes to finish before republishing.'))

    cycle_id = uuid4()
    for account in accounts:
        event = record(
            AuditEvent.CREDENTIAL_REPUBLISHED, credential=credential, account=account,
            applications=[app for app in applications if account.id in allowed[app.id]],
            credential_key=credential.account_key(account.id), revision=account.version,
            operation_id=cycle_id, source=AuditSource.ADMINISTRATOR, operator=operator,
        )
        enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED)
    return credential, cycle_id
