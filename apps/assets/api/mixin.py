from typing import List

from rest_framework.request import Request

from assets.models import Node, Platform, Protocol
from assets.utils import get_node_from_request, is_query_node_all_assets
from common.utils import lazyproperty, timeit


class SerializeToTreeNodeMixin:
    request: Request

    @lazyproperty
    def is_sync(self):
        sync_paths = ['/api/v1/perms/users/self/nodes/all-with-assets/tree/']
        for p in sync_paths:
            if p == self.request.path:
                return True
        return False

    @timeit
    def serialize_nodes(self, nodes: List[Node], with_asset_amount=False):
        if with_asset_amount:
            def _name(node: Node):
                return '{} ({})'.format(node.value, node.assets_amount)
        else:
            def _name(node: Node):
                return node.value

        def _open(node):
            if not self.is_sync:
                # 异步加载资产树时，默认展开节点
                return True
            if not node.parent_key:
                return True
            else:
                return False

        data = [
            {
                'id': node.key,
                'name': _name(node),
                'title': _name(node),
                'pId': node.parent_key,
                'isParent': True,
                'open': _open(node),
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

    @lazyproperty
    def support_types(self):
        from assets.const import AllTypes
        return AllTypes.get_types_values(exclude_custom=True)

    def get_icon(self, asset):
        if asset.category == 'device':
            return 'switch'
        if asset.type in self.support_types:
            return asset.type
        else:
            return 'file'

    @timeit
    def serialize_assets(self, assets, node_key=None, get_pid=None):
        if not get_pid and not node_key:
            get_pid = lambda asset, platform: getattr(asset, 'parent_key', '')

        sftp_asset_ids = Protocol.objects.filter(name='sftp') \
            .values_list('asset_id', flat=True)
        sftp_asset_ids = set(sftp_asset_ids)
        platform_map = {p.id: p for p in Platform.objects.all()}

        data = []
        root_assets_count = 0
        for asset in assets:
            platform = platform_map.get(asset.platform_id)
            if not platform:
                continue
            pid = node_key or get_pid(asset, platform)
            if not pid:
                continue
            # 根节点最多显示 1000 个资产
            if pid.isdigit():
                if root_assets_count > 1000:
                    continue
                root_assets_count += 1
            data.append({
                'id': str(asset.id),
                'name': asset.name,
                'title': f'{asset.address}\n{asset.comment}'.strip(),
                'pId': pid,
                'isParent': False,
                'open': False,
                'iconSkin': self.get_icon(platform),
                'chkDisabled': not asset.is_active,
                'meta': {
                    'type': 'asset',
                    'data': {
                        'platform_type': platform.type,
                        'org_name': asset.org_name,
                        'sftp': asset.id in sftp_asset_ids,
                        'name': asset.name,
                        'address': asset.address
                    },
                }
            })
        return data


class NodeFilterMixin:
    request: Request

    @lazyproperty
    def is_query_node_all_assets(self):
        return is_query_node_all_assets(self.request)

    @lazyproperty
    def node(self):
        return get_node_from_request(self.request)
