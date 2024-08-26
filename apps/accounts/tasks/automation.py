import datetime

from celery import shared_task
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext_noop

from accounts.const import AutomationTypes
from accounts.tasks.common import quickstart_automation_by_snapshot
from common.const.crontab import CRONTAB_AT_AM_THREE
from common.utils import get_logger, get_object_or_none, get_log_keep_day
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_org, tmp_to_root_org

logger = get_logger(__file__)


def task_activity_callback(self, pid, trigger, tp, *args, **kwargs):
    model = AutomationTypes.get_type_model(tp)
    with tmp_to_root_org():
        instance = get_object_or_none(model, pk=pid)
    if not instance:
        return
    if not instance.latest_execution:
        return
    resource_ids = instance.latest_execution.get_all_asset_ids()
    return resource_ids, instance.org_id


@shared_task(
    queue='ansible', verbose_name=_('Account execute automation'),
    activity_callback=task_activity_callback
)
def execute_account_automation_task(pid, trigger, tp):
    model = AutomationTypes.get_type_model(tp)
    with tmp_to_root_org():
        instance = get_object_or_none(model, pk=pid)
    if not instance:
        logger.error("No automation task found: {}".format(pid))
        return
    with tmp_to_org(instance.org):
        instance.execute(trigger)


def record_task_activity_callback(self, record_ids, *args, **kwargs):
    from accounts.models import ChangeSecretRecord
    with tmp_to_root_org():
        records = ChangeSecretRecord.objects.filter(id__in=record_ids)
    if not records:
        return
    resource_ids = [str(i.id) for i in records]
    org_id = records[0].execution.org_id
    return resource_ids, org_id


@shared_task(
    queue='ansible', verbose_name=_('Execute automation record'),
    activity_callback=record_task_activity_callback
)
def execute_automation_record_task(record_ids, tp):
    from accounts.models import ChangeSecretRecord
    task_name = gettext_noop('Execute automation record')

    with tmp_to_root_org():
        records = ChangeSecretRecord.objects.filter(id__in=record_ids)

    if not records:
        logger.error('No automation record found: {}'.format(record_ids))
        return

    record = records[0]
    record_map = {f'{record.asset_id}-{record.account_id}': str(record.id) for record in records}
    task_snapshot = {
        'params': {},
        'record_map': record_map,
        'secret': record.new_secret,
        'secret_type': record.execution.snapshot.get('secret_type'),
        'assets': [str(instance.asset_id) for instance in records],
        'accounts': [str(instance.account_id) for instance in records],
    }
    with tmp_to_org(record.execution.org_id):
        quickstart_automation_by_snapshot(task_name, tp, task_snapshot)


@shared_task(
    verbose_name=_('Clean change secret and push record period'),
    description=_('Clean change secret and push record period')
)
@register_as_period_task(crontab=CRONTAB_AT_AM_THREE)
def clean_change_secret_and_push_record_period():
    from accounts.models import ChangeSecretRecord
    print('Start clean change secret and push record period')
    with tmp_to_root_org():
        now = timezone.now()
        days = get_log_keep_day('ACCOUNT_CHANGE_SECRET_RECORD_KEEP_DAYS')
        expired_day = now - datetime.timedelta(days=days)
        records = ChangeSecretRecord.objects.filter(
            date_updated__lt=expired_day
        ).filter(
            Q(execution__isnull=True) | Q(asset__isnull=True) | Q(account__isnull=True)
        )

        records.delete()
