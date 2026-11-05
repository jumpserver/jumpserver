import json
import uuid
from tempfile import TemporaryFile

from celery import shared_task, current_task
from django.conf import settings
from django.db import router, transaction
from django.db.models import Count, Q
from django.utils.translation import gettext_noop, gettext_lazy as _

from accounts.const import AutomationTypes
from accounts.models import Account
from accounts.tasks.common import quickstart_automation_by_snapshot
from audits.const import ActivityChoices
from common.const.crontab import CRONTAB_AT_AM_TWO
from common.utils import get_logger
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org

logger = get_logger(__file__)

__all__ = ['remove_accounts_task']


@shared_task(
    queue="ansible",
    verbose_name=_('Remove account'),
    activity_callback=lambda self, gather_account_ids, *args, **kwargs: (gather_account_ids, None),
    description=_(
        """When clicking "Sync deletion" in 'Console - Gather Account - Gathered accounts' this 
        task will be executed"""
    )
)
def remove_accounts_task(gather_account_ids):
    from accounts.models import GatheredAccount

    gather_accounts = GatheredAccount.objects.filter(
        id__in=gather_account_ids
    )
    task_name = gettext_noop("Remove account")

    task_snapshot = {
        'assets': [str(i.asset_id) for i in gather_accounts],
        'accounts': [{'asset': str(i.asset_id), 'username': i.username} for i in gather_accounts],
    }

    tp = AutomationTypes.remove_account
    quickstart_automation_by_snapshot(task_name, tp, task_snapshot)


def _iter_obsolete_history_batches(history_model, keep_count, batch_size=500, *, using=None):
    # HistoricalAccount has an auto-increment history_id. Leave histories
    # created during this run for the next cleanup, including backdated ones.
    manager = history_model.objects.using(using)
    last_history_id = manager.order_by('-history_id').values_list(
        'history_id', flat=True,
    ).first()
    if last_history_id is None:
        return
    histories = manager.filter(history_id__lte=last_history_id)
    accounts = histories.order_by('id').values('id').annotate(
        count=Count('history_id'),
    ).filter(count__gt=keep_count).values_list('id', flat=True)

    last_account_id = None
    while True:
        page = accounts if last_account_id is None else accounts.filter(id__gt=last_account_id)
        account_ids = list(page[:batch_size])
        if not account_ids:
            return
        last_account_id = account_ids[-1]
        for account_id in account_ids:
            account_histories = histories.filter(id=account_id)
            # Match simple-history's newest-first ordering, including ties.
            cutoff = list(account_histories.order_by(
                '-history_date', '-history_id',
            ).values_list('history_date', 'history_id')[keep_count - 1:keep_count])
            if not cutoff:
                continue
            cutoff_date, cutoff_id = cutoff[0]
            obsolete = account_histories.filter(
                Q(history_date__lt=cutoff_date)
                | Q(history_date=cutoff_date, history_id__lt=cutoff_id)
            ).order_by('history_id')
            last_deleted_id = None
            while True:
                page = obsolete if last_deleted_id is None else obsolete.filter(
                    history_id__gt=last_deleted_id,
                )
                history_ids = list(page.values_list('history_id', flat=True)[:batch_size])
                if not history_ids:
                    break
                last_deleted_id = history_ids[-1]
                # Keep the account, snapshot and retention filters on deletion.
                yield obsolete.filter(history_id__in=history_ids)


@shared_task(
    verbose_name=_('Clean historical accounts'),
    description=_(
        """Each time an asset account is updated, a historical account is generated, so it is 
        necessary to clean up the asset account history. The system will clean up excess account 
        records at 2 a.m. daily based on the configuration in the "System settings - Features - 
        Account storage - Record limit"""
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
@tmp_to_root_org()
def clean_historical_accounts():
    from audits.signal_handlers import create_activities
    print("Clean historical accounts start.")
    if settings.HISTORY_ACCOUNT_CLEAN_LIMIT >= 999:
        return
    limit = settings.HISTORY_ACCOUNT_CLEAN_LIMIT
    limit += 1  # 因为当前账号的密码是最新的那条历史记录，因此保留 n 条历史，实际上应该保留 n+1 条历史记录

    task_id = current_task.request.id if current_task else str(uuid.uuid4())
    detail = gettext_noop('Remove historical accounts that are out of range.')
    history_model = Account.history.model
    using = router.db_for_write(history_model)
    # Keep the original commit boundary: delete all histories first, then write
    # activities. An activity failure must not restore rows whose Vault secrets
    # were already removed by post_delete. This private file holds only IDs.
    with TemporaryFile(mode='w+t', encoding='utf-8') as activity_batches:
        with transaction.atomic(using=using):
            for history_qs in _iter_obsolete_history_batches(history_model, limit, using=using):
                # Recheck and lock the bounded batch so concurrent cleanup cannot
                # produce duplicate deletion activities for rows already removed.
                resource_ids = list(history_qs.select_for_update().values_list('history_id', flat=True))
                if not resource_ids:
                    continue
                activity_batches.write(json.dumps(resource_ids) + '\n')
                # ORM deletion is required: post_delete also removes Vault entries.
                history_qs.filter(history_id__in=resource_ids).delete()
            activity_batches.flush()
        activity_batches.seek(0)
        for line in activity_batches:
            create_activities(json.loads(line), detail, task_id, action=ActivityChoices.task, org_id='')
