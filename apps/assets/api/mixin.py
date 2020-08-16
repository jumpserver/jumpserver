from typing import List

from assets.models import Node, Asset
from assets.pagination import AssetLimitOffsetPagination
from common.utils import lazyproperty, dict_get_any, is_uuid, get_object_or_none


class SerializeToTreeNodeMixin:
    permission_classes = ()

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
                'open': node.is_org_root(),
                'meta': {
                    'node': {
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

    def get_platform(self, asset: Asset):
        default = 'file'
        icon = {'windows', 'linux'}
        platform = asset.platform_base.lower()
        if platform in icon:
            return platform
        return default

    def serialize_assets(self, assets, node_key=None, with_org_name=False):
        if node_key is None:
            get_pid = lambda asset: getattr(asset, 'parent_key', '')
        else:
            get_pid = lambda asset: node_key

        if with_org_name:
            get_org_name = lambda asset: asset.org_name
        else:
            get_org_name = lambda asset: None

        data = [
            {
                'id': str(asset.id),
                'name': asset.hostname,
                'title': asset.ip,
                'pId': get_pid(asset),
                'isParent': False,
                'open': False,
                'iconSkin': self.get_platform(asset),
                'nocheck': not asset.has_protocol('ssh'),
                'meta': {
                    'type': 'asset',
                    'asset': {
                        'id': asset.id,
                        'hostname': asset.hostname,
                        'ip': asset.ip,
                        'protocols': asset.protocols_as_list,
                        'platform': asset.platform_base,
                        'domain': asset.domain_id,
                        'org_name': get_org_name(asset),
                        'org_id': asset.org_id
                    },
                }
            }
            for asset in assets
        ]
        return data


class FilterAssetByNodeMixin:
    pagination_class = AssetLimitOffsetPagination

    @lazyproperty
    def is_query_node_all_assets(self):
        request = self.request
        query_all_arg = request.query_params.get('all')
        show_current_asset_arg = request.query_params.get('show_current_asset')
        if show_current_asset_arg is not None:
            return show_current_asset_arg != '1'
        return query_all_arg == '1'

    @lazyproperty
    def node(self):
        node_id = dict_get_any(self.request.query_params, ['node', 'node_id'])
        if not node_id:
            return None

        if is_uuid(node_id):
            node = get_object_or_none(Node, id=node_id)
        else:
            node = get_object_or_none(Node, key=node_id)
        return node
