from celery import shared_task
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from accounts.const import Source
from common.utils import get_logger
from orgs.utils import tmp_to_root_org, tmp_to_org

logger = get_logger(__name__)


@shared_task(
    verbose_name=_('Template sync info to related accounts'),
    activity_callback=lambda self, template_id, *args, **kwargs: (template_id, None),
    description=_(
        'Synchronize template properties to following accounts without changing credentials.'
    ),
)
def template_sync_related_accounts(template_id, user_id=None):
    from accounts.models import Account, AccountTemplate

    with tmp_to_root_org():
        template = AccountTemplate.objects.filter(id=template_id).first()
    if template is None:
        return

    succeeded, failed = 0, 0
    with tmp_to_org(template.org_id):
        account_ids = list(Account.objects.filter(
            source=Source.TEMPLATE, source_id=template_id, follow_template=True,
        ).values_list('id', flat=True))
        for account_id in account_ids:
            try:
                with transaction.atomic():
                    # Recheck following after locking: a queued task must respect opt-outs.
                    account = Account.objects.select_for_update().filter(
                        id=account_id, source=Source.TEMPLATE,
                        source_id=template_id, follow_template=True,
                    ).first()
                    if account is None:
                        continue
                    changed = []
                    for field in Account.TEMPLATE_SYNC_FIELDS:
                        value = getattr(template, field)
                        if getattr(account, field) != value:
                            setattr(account, field, value)
                            changed.append(field)
                    if changed:
                        # Property synchronization must not read or write external secrets.
                        account.skip_vault_when_saving = True
                        account.skip_history_when_saving = True
                        account.save(update_fields=changed)
                    succeeded += 1
            except Exception:
                # Preserve provenance and following so a failed account can be retried.
                logger.exception('Template sync failed for account %s', account_id)
                failed += 1
    print(f'Template sync completed: succeeded={succeeded}, failed={failed}')
