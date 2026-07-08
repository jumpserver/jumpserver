from django.utils import timezone

from assets.models import Asset
from common.decorators import merge_delay_run
from orgs.utils import tmp_to_root_org


@merge_delay_run(ttl=5)
def update_assets_last_login_date(asset_ids=()):
    if not asset_ids:
        return

    with tmp_to_root_org():
        Asset.objects.filter(id__in=asset_ids).update(
            date_last_login=timezone.now()
        )
