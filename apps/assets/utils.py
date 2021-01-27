# ~*~ coding: utf-8 ~*~
#
from assets.tree import Tree
from common.utils import get_logger, dict_get_any, is_uuid, get_object_or_none
from common.utils.common import random_string
from common.http import is_true
from orgs.utils import current_org
from .models import Asset, Node, NodeAssetRelatedRecord
from assets.locks import NodeTreeUpdateLock

logger = get_logger(__file__)


def check_node_assets_amount():
    if current_org.is_root():
        logger.error(f'Can not run check_node_assets_amount in root org')
        return

    with NodeTreeUpdateLock():
        ident = random_string(6)
        logger.info(f'[{ident}] Begin check node assets amount in {current_org}')
        nodes = list(Node.objects.exclude(key__startswith='-').only('id', 'key', 'parent_key'))
        node_asset_id_pairs = Asset.nodes.through.objects.all().values_list('node_id', 'asset_id')
        tree = Tree(nodes, node_asset_id_pairs)
        tree.build_tree()
        tree.compute_tree_node_assets_amount()
        logger.info(f'[{ident}] Prepared data completed, check nodes one by one ...')

        for node in nodes:
            tree_node = tree.key_tree_node_mapper[node.key]
            if tree_node.assets_amount != node.assets_amount:
                logger.warn(f'[{ident}] Node wrong assets amount <Node:{node.key}> '
                            f'{node.assets_amount} right is {tree_node.assets_amount}')
                node.assets_amount = tree_node.assets_amount
                node.save()
        logger.info(f'[{ident}] Finish check node assets amount in {current_org}')


def is_query_node_all_assets(request):
    request = request
    query_all_arg = request.query_params.get('all', 'true')
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
