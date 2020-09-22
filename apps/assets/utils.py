# ~*~ coding: utf-8 ~*~
#
from django.db.models import Q

from common.utils import get_logger
from .models import Asset, Node


logger = get_logger(__file__)


def check_node_assets_amount():
    for node in Node.objects.all():
        assets_amount = Asset.objects.filter(
            Q(nodes__key__istartswith=f'{node.key}:') | Q(nodes=node)
        ).distinct().count()

        if node.assets_amount != assets_amount:
            print(f'>>> <Node:{node.key}> wrong assets amount '
                  f'{node.assets_amount} right is {assets_amount}')
            node.assets_amount = assets_amount
            node.save()


def is_asset_exists_in_node(asset_pk, node_key):
    return Asset.objects.filter(
        id=asset_pk
    ).filter(
        Q(nodes__key__istartswith=f'{node_key}:') | Q(nodes__key=node_key)
    ).exists()
