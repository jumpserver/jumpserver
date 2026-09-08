from typing import List

from rest_framework.request import Request
from rest_framework.response import Response

from assets.models import Node, Platform, Protocol, MyAsset
from assets.utils import (
    attach_nodes_realtime_assets_amount, get_node_from_request,
    is_query_node_all_assets,
)
from common.utils import lazyproperty, timeit


class NodeAssetsAmountListMixin:
    """Attach exact subtree asset amounts after filtering and pagination."""

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        nodes = page if page is not None else queryset
        nodes = attach_nodes_realtime_assets_amount(nodes)
        serializer = self.get_serializer(nodes, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


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
    def serialize_nodes(
            self, nodes: List[Node], with_asset_amount=False,
            with_has_children=True,
    ):
        if with_asset_amount:
            def _name(node: Node):
                amount = getattr(
                    node, 'assets_amount_realtime', node.assets_amount
                )
                return '{} ({})'.format(node.value, amount)
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

        def _has_children(node):
            # Callers that have not opted into the annotation keep the
            # previous lazy-tree behaviour.
            return bool(getattr(node, 'has_children', True))

        data = []
        for node in nodes:
            item = {
                'id': node.key,
                'name': _name(node),
                'title': _name(node),
                'pId': node.parent_key,
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
            if with_has_children:
                has_children = _has_children(node)
                item.update({
                    'isParent': has_children,
                    'hasChildren': has_children,
                })
                item['meta']['data']['has_children'] = has_children
            data.append(item)
        return data

    @timeit
    def serialize_compact_nodes(self, rows):
        """Serialize the minimal node shape consumed by XTree."""
        rows = list(rows)
        parent_keys = {
            parent_key for _, _, _, parent_key in rows if parent_key
        }
        return [
            {
                'id': key,
                'name': value,
                'pId': parent_key,
                'hasChildren': key in parent_keys,
                'meta': {
                    'type': 'node',
                    'data': {'id': node_id},
                },
            }
            for node_id, key, value, parent_key in rows
        ]

    @lazyproperty
    def support_types(self):
        from assets.const import AllTypes
        return AllTypes.get_types_values(exclude_custom=True)

    def get_icon(self, asset):
        return asset.get_icon_skin()
        
    @timeit
    def serialize_assets(self, assets, node_key=None, get_pid=None):
        assets = list(assets)
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
            platform = platform_map.get(asset.platform_id)
            if not platform:
                continue
            pid = node_key or get_pid(asset, platform)
            if not pid:
                continue
            # 根节点最多显示 1000 个资产
            if pid.isdigit():
                if root_assets_count >= 1000:
                    continue
                root_assets_count += 1
            data.append({
                'id': str(asset.id),
                'name': asset.name,
                'title': f'{asset.address}\n{asset.comment}'.strip(),
                'pId': pid,
                'isParent': False,
                'open': False,
                'iconSkin': self.get_icon(asset),
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
