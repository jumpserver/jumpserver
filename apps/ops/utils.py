# ~*~ coding: utf-8 ~*~
import os
import uuid
from django.conf import settings

from common.utils import get_logger, make_dirs
from jumpserver.const import PROJECT_DIR
from perms.models import PermNode
from perms.utils import UserPermAssetUtil
from assets.models import Asset, Node

logger = get_logger(__file__)


def get_task_log_path(base_path, task_id, level=2):
    task_id = str(task_id)
    try:
        uuid.UUID(task_id)
    except:
        return os.path.join(PROJECT_DIR, 'data', 'caution.txt')

    rel_path = os.path.join(*task_id[:level], task_id + '.log')
    path = os.path.join(base_path, rel_path)
    make_dirs(os.path.dirname(path), exist_ok=True)
    return path


def get_ansible_log_verbosity(verbosity=0):
    if settings.DEBUG_ANSIBLE:
        return 10
    if verbosity is None and settings.DEBUG:
        return 1
    return verbosity


def merge_nodes_and_assets(nodes, assets, user):
    if not nodes:
        return assets
    perm_util = UserPermAssetUtil(user=user)
    for node_id in nodes:
        if isinstance(node_id, Node):
            node_id = node_id.id
        if node_id == PermNode.FAVORITE_NODE_KEY:
            node_assets = perm_util.get_favorite_assets()
        elif node_id == PermNode.UNGROUPED_NODE_KEY:
            node_assets = perm_util.get_ungroup_assets()
        else:
            node, node_assets = perm_util.get_node_all_assets(node_id)
        assets.extend(node_assets.exclude(id__in=[asset.id for asset in assets]))
    return assets
