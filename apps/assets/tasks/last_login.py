from celery import shared_task
from django.utils.translation import gettext_lazy as _

from assets.models import Asset
from assets.utils.last_login import BATCH_SIZE, asset_last_login_buffer
from common.utils.lock import DistributedLock
from ops.celery.decorator import after_app_ready_start, register_as_period_task
from orgs.utils import tmp_to_root_org


def apply_asset_last_login_updates(updates):
    if not updates:
        return 0

    assets = Asset.objects.filter(id__in=updates).only('id', 'date_last_login')
    changed = []
    for asset in assets:
        date_last_login = updates[str(asset.id)]
        if (
                asset.date_last_login is not None and
                asset.date_last_login >= date_last_login
        ):
            continue
        asset.date_last_login = date_last_login
        changed.append(asset)

    if changed:
        Asset.objects.bulk_update(
            changed,
            fields=['date_last_login'],
            batch_size=BATCH_SIZE,
        )
    return len(changed)


@shared_task(
    verbose_name=_('Update asset last login time'),
    description=_('Periodically persist merged asset last login times'),
)
@register_as_period_task(interval=10)
@after_app_ready_start
@tmp_to_root_org()
def flush_asset_last_login_periodic():
    with DistributedLock('asset-last-login-flush', expire=30):
        updates = asset_last_login_buffer.get_due()
        updated = apply_asset_last_login_updates(updates)
        asset_last_login_buffer.ack(updates)
    return updated
