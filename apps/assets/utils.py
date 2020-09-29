# ~*~ coding: utf-8 ~*~
#
from django.db.models import Q

from common.utils import get_logger, dict_get_any, is_uuid, get_object_or_none
from common.http import is_true
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


def is_query_node_all_assets(request):
    request = request
    query_all_arg = request.query_params.get('all')
    show_current_asset_arg = request.query_params.get('show_current_asset')
    if show_current_asset_arg is not None:
        return not is_true(show_current_asset_arg)
    return is_true(query_all_arg)


def get_node(request):
    node_id = dict_get_any(request.query_params, ['node', 'node_id'])
    if not node_id:
        return None

    if is_uuid(node_id):
        node = get_object_or_none(Node, id=node_id)
    else:
        node = get_object_or_none(Node, key=node_id)
    return node
