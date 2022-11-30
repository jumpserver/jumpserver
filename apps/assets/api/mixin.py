from typing import List

from rest_framework.request import Request

from assets.models import Node
from assets.utils import get_node_from_request, is_query_node_all_assets
from common.utils import lazyproperty, timeit


class SerializeToTreeNodeMixin:

    @timeit
    def serialize_nodes(self, nodes: List[Node], with_asset_amount=False):
        if with_asset_amount:
            def _name(node: Node):
                return '{} ({})'.format(node.value, node.assets_amount)
        else:
            def _name(node: Node):
                return node.value
        data = [
            {
                'id': node.key,
                'name': _name(node),
                'title': _name(node),
                'pId': node.parent_key,
                'isParent': True,
                'open': True,
                'meta': {
                    'data': {
                        "id": node.id,
                        "key": node.key,
                        "value": node.value,
                    },
                    'type': 'node'
                }
            }
            for node in nodes
        ]
        return data

    @timeit
    def serialize_assets(self, assets, node_key=None):
        if node_key is None:
            get_pid = lambda asset: getattr(asset, 'parent_key', '')
        else:
            get_pid = lambda asset: node_key

        data = [
            {
                'id': str(asset.id),
                'name': asset.name,
                'title': asset.address,
                'pId': get_pid(asset),
                'isParent': False,
                'open': False,
                'iconSkin': asset.type,
                'chkDisabled': not asset.is_active,
                'meta': {
                    'type': 'asset',
                    'data': {
                        'org_name': asset.org_name
                    },
                }
            }
            for asset in assets
        ]
        return data


class NodeFilterMixin:
    request: Request

    @lazyproperty
    def is_query_node_all_assets(self):
        return is_query_node_all_assets(self.request)

    @lazyproperty
    def node(self):
        return get_node_from_request(self.request)
