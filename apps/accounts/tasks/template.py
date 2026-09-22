from celery import shared_task
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from accounts.const import Source
from common.utils import get_logger
from orgs.utils import tmp_to_root_org, tmp_to_org

logger = get_logger(__name__)


class TemplateCredentialSyncError(Exception):
    pass


@shared_task(
    verbose_name=_('Template sync info to related accounts'),
    autoretry_for=(TemplateCredentialSyncError,),
    retry_backoff=30,
    retry_backoff_max=300,
    retry_kwargs={'max_retries': 3},
    activity_callback=lambda self, template_id, *args, **kwargs: (template_id, None),
    description=_(
        'Synchronize template credentials to following accounts.'
    ),
)
def template_sync_related_accounts(template_id, user_id=None, initialize=False):
    from accounts.models import Account, AccountTemplate

    with tmp_to_root_org():
        template = AccountTemplate.objects.filter(id=template_id).first()
    if template is None:
        return

    succeeded, failed = 0, []
    with tmp_to_org(template.org_id):
        account_ids = list(Account.objects.filter(
            source=Source.TEMPLATE, source_id=template_id, follow_template=True,
        ).values_list('id', flat=True))
        for account_id in account_ids:
            try:
                with transaction.atomic(using=Account.objects.db):
                    # Recheck following after locking: a queued task must respect opt-outs.
                    account = Account.objects.select_for_update().filter(
                        id=account_id, source=Source.TEMPLATE,
                        source_id=template_id, follow_template=True,
                    ).first()
                    if account is None:
                        continue
                    if initialize and not account.secret_has_save_to_vault:
                        # Upgrade accounts created by the old dynamic-reference implementation.
                        from accounts.backends import vault_client
                        from accounts.exceptions import VaultSecretNotFoundException
                        try:
                            vault_client.get_for_restore(account)
                        except VaultSecretNotFoundException:
                            account._create_vault_entry = True
                    # Read the latest template after locking this account so older
                    # queued tasks cannot overwrite a newer synchronization.
                    if account.copy_template_credentials(
                        only_if_changed=not initialize or account.secret_has_save_to_vault,
                    ):
                        account.save(update_fields=['secret'])
                    succeeded += 1
            except Exception:
                # Preserve provenance and following so a failed account can be retried.
                logger.exception('Template sync failed for account %s', account_id)
                failed.append(str(account_id))
    print(f'Template sync completed: succeeded={succeeded}, failed={len(failed)}')
    if failed:
        raise TemplateCredentialSyncError(f'Template {template_id}: failed accounts: {", ".join(failed)}')
    return {'succeeded': succeeded, 'failed': failed}
