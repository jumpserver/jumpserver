import os
import sys

import django

if os.path.exists('../apps'):
    sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
    sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from assets.models import Asset as asset_model, Host as host_model, Device as device_model
from orgs.models import Organization


def clean_host():
    root = Organization.root()
    root.change_to()

    devices = host_model.objects.filter(platform__category='device')
    assets = asset_model.objects.filter(id__in=devices.values_list('asset_ptr_id', flat=True))
    assets_map = {asset.id: asset for asset in assets}

    for host in devices:
        asset = assets_map.get(host.asset_ptr_id)
        if not asset:
            continue
        device = device_model(asset_ptr_id=asset.id)
        device.__dict__.update(asset.__dict__)
        device.save()
        host.delete(keep_parents=True)


if __name__ == "__main__":
    clean_host()
