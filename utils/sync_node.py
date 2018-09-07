#!/usr/bin/python
import os
import sys
import django

if os.path.exists('../apps'):
	sys.path.insert(0, '../apps')
elif os.path.exists('./apps'):
	sys.path.insert(0, './apps')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from assets.models import Node, Asset
from common.utils import get_object_or_none
from django.db import transaction

src_node = Node.objects.get(key="0:1")
target_node = Node.objects.get(key="2:1")

def sync_node(src, target, cut=False):
    assets = src.get_assets()
	# 同步本节点资产
    for asset in assets:
        if cut:
            src.assets.remove(asset)
            asset.org_id = target.org_id
            asset.save()
            new_asset = asset
        else:
            new_asset = get_object_or_none(Asset, hostname=asset.hostname, org_id=target.org_id)
            if new_asset is None:
                asset.id = None
                asset.org_id = target.org_id
                asset.save()
                new_asset = asset
        target.assets.add(new_asset)
	# 同步子节点资产
    for child in src.get_children():
        node_new = target.create_child(child.value)
        node_new.org_id = target.org_id
        node_new.save()
        sync_node(child, node_new)

if __name__ == '__main__':
    with transaction.atomic():
        sync_node(src_node, target_node)

