from typing import List

from rest_framework.request import Request

from assets.models import Platform, Protocol, MyAsset
from common.utils import lazyproperty, timeit
from assets.tree.asset_tree import AssetTreeNode, AssetTreeNodeAsset

from .const import RenderTreeType


__all__ = ['SerializeToTreeNodeMixin']


class SerializeToTreeNodeMixin:
    request: Request

    @timeit
    def serialize_nodes(self, nodes: List[AssetTreeNode], tree_type: RenderTreeType, 
                        with_asset_amount=False, expand_level=1):
        if not nodes:
            return []

        def _name(node: AssetTreeNode):
            v = node.value
            if not with_asset_amount:
                return v
            v = f'{v} ({node.assets_amount_total})'
            return v
        
        def is_parent(node: AssetTreeNode):
            if tree_type.is_asset_tree:
                return node.assets_amount > 0 or not node.is_leaf
            elif tree_type.is_node_tree:
                return not node.is_leaf
            else:
                return True

        data = [
            {
                'id': node.key,
                'name': _name(node),
                'title': _name(node),
                'pId': node.parent_key,
                'isParent': is_parent(node),
                'open': node.level <= expand_level,
                'meta': {
                    'type': 'node',
                    'data': {
                        "id": node.id,
                        "key": node.key,
                        "value": node.value,
                        "assets_amount": node.assets_amount,
                        "assets_amount_total": node.assets_amount_total,
                        "children_count_total": node.children_count_total,
                    },
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
        if not assets:
            return []

        if not get_pid and not node_key:
            get_pid = lambda asset, platform: getattr(asset, 'parent_key', '')

        sftp_asset_ids = Protocol.objects.filter(name='sftp') \
            .values_list('asset_id', flat=True)
        sftp_asset_ids = set(sftp_asset_ids)
        platform_map = {p.id: p for p in Platform.objects.all()}

        data = []
        root_assets_count = 0
        MyAsset.set_asset_custom_value(assets, self.request.user)
        for asset in assets:
            asset: AssetTreeNodeAsset
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