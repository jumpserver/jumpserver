import uuid
from collections import defaultdict

from celery import shared_task, current_task
from django.conf import settings
from django.db.models import Count
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
    queue="ansible", verbose_name=_('Remove account'),
    activity_callback=lambda self, gather_account_ids, *args, **kwargs: (gather_account_ids, None)
)
def remove_accounts_task(gather_account_ids):
    from accounts.models import GatheredAccount

    gather_accounts = GatheredAccount.objects.filter(
        id__in=gather_account_ids
    )
    task_name = gettext_noop("Remove account")

    task_snapshot = {
        'assets': [str(i.asset_id) for i in gather_accounts],
        'gather_accounts': [str(i.id) for i in gather_accounts],
    }

    tp = AutomationTypes.remove_account
    quickstart_automation_by_snapshot(task_name, tp, task_snapshot)


@shared_task(verbose_name=_('Clean historical accounts'))
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
@tmp_to_root_org()
def clean_historical_accounts():
    from audits.signal_handlers import create_activities
    print("Clean historical accounts start.")
    if settings.HISTORY_ACCOUNT_CLEAN_LIMIT >= 999:
        return
    limit = settings.HISTORY_ACCOUNT_CLEAN_LIMIT

    history_ids_to_be_deleted = []
    history_model = Account.history.model
    history_id_mapper = defaultdict(list)

    ids = history_model.objects.values('id').annotate(count=Count('id', distinct=True)) \
        .filter(count__gte=limit).values_list('id', flat=True)

    if not ids:
        return

    for i in history_model.objects.filter(id__in=ids):
        _id = str(i.id)
        history_id_mapper[_id].append(i.history_id)

    for history_ids in history_id_mapper.values():
        history_ids_to_be_deleted.extend(history_ids[limit:])
    history_qs = history_model.objects.filter(history_id__in=history_ids_to_be_deleted)

    resource_ids = list(history_qs.values_list('history_id', flat=True))
    history_qs.delete()

    task_id = current_task.request.id if current_task else str(uuid.uuid4())
    detail = gettext_noop('Remove historical accounts that are out of range.')
    create_activities(resource_ids, detail, task_id, action=ActivityChoices.task, org_id='')
