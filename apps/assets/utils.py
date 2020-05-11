# ~*~ coding: utf-8 ~*~
#
from treelib import Tree
from treelib.exceptions import NodeIDAbsentError
from collections import defaultdict
from copy import deepcopy

from common.utils import get_logger, timeit, lazyproperty
from .models import Asset, Node


logger = get_logger(__file__)


class TreeService(Tree):
    tag_sep = ' / '

    @staticmethod
    @timeit
    def get_nodes_assets_map():
        nodes_assets_map = defaultdict(set)
        asset_node_list = Node.assets.through.objects.values_list(
            'asset', 'node__key'
        )
        for asset_id, key in asset_node_list:
            nodes_assets_map[key].add(asset_id)
        return nodes_assets_map

    @classmethod
    @timeit
    def new(cls):
        from .models import Node
        all_nodes = list(Node.objects.all().values("key", "value"))
        all_nodes.sort(key=lambda x: len(x["key"].split(":")))
        tree = cls()
        tree.create_node(tag='', identifier='', data={})
        for node in all_nodes:
            key = node["key"]
            value = node["value"]
            parent_key = ":".join(key.split(":")[:-1])
            tree.safe_create_node(
                tag=value, identifier=key,
                parent=parent_key,
            )
        tree.init_assets()
        return tree

    def init_assets(self):
        node_assets_map = self.get_nodes_assets_map()
        for node in self.all_nodes_itr():
            key = node.identifier
            assets = node_assets_map.get(key, set())
            data = {"assets": assets, "all_assets": None}
            node.data = data

    def safe_create_node(self, **kwargs):
        parent = kwargs.get("parent")
        if not self.contains(parent):
            kwargs['parent'] = self.root
        self.create_node(**kwargs)

    def all_children_ids(self, nid, with_self=True):
        children_ids = self.expand_tree(nid)
        if not with_self:
            next(children_ids)
        return list(children_ids)

    def all_children(self, nid, with_self=True, deep=False):
        children_ids = self.all_children_ids(nid, with_self=with_self)
        return [self.get_node(i, deep=deep) for i in children_ids]

    def ancestors_ids(self, nid, with_self=True):
        ancestor_ids = list(self.rsearch(nid))
        ancestor_ids.pop()
        if not with_self:
            ancestor_ids.pop(0)
        return ancestor_ids

    def ancestors(self, nid, with_self=False, deep=False):
        ancestor_ids = self.ancestors_ids(nid, with_self=with_self)
        ancestors = [self.get_node(i, deep=deep) for i in ancestor_ids]
        return ancestors

    def get_node_full_tag(self, nid):
        ancestors = self.ancestors(nid, with_self=True)
        ancestors.reverse()
        return self.tag_sep.join([n.tag for n in ancestors])

    def get_family(self, nid, deep=False):
        ancestors = self.ancestors(nid, with_self=False, deep=deep)
        children = self.all_children(nid, with_self=False)
        return ancestors + [self[nid]] + children

    @staticmethod
    def is_parent(child, parent):
        parent_id = child.bpointer
        return parent_id == parent.identifier

    def root_node(self):
        return self.get_node(self.root)

    def get_node(self, nid, deep=False):
        node = super().get_node(nid)
        if deep:
            node = self.copy_node(node)
            node.data = {}
        return node

    def parent(self, nid, deep=False):
        parent = super().parent(nid)
        if deep:
            parent = self.copy_node(parent)
        return parent

    @lazyproperty
    def invalid_assets(self):
        assets = Asset.objects.filter(is_active=False).values_list('id', flat=True)
        return assets

    def set_assets(self, nid, assets):
        node = self.get_node(nid)
        if node.data is None:
            node.data = {}
        node.data["assets"] = assets

    def assets(self, nid):
        node = self.get_node(nid)
        return node.data.get("assets", set())

    def valid_assets(self, nid):
        return set(self.assets(nid)) - set(self.invalid_assets)

    def all_assets(self, nid):
        node = self.get_node(nid)
        if node.data is None:
            node.data = {}
        all_assets = node.data.get("all_assets")
        if all_assets is not None:
            return all_assets
        all_assets = set(self.assets(nid))
        try:
            children = self.children(nid)
        except NodeIDAbsentError:
            children = []
        for child in children:
            all_assets.update(self.all_assets(child.identifier))
        node.data["all_assets"] = all_assets
        return all_assets

    def all_valid_assets(self, nid):
        return set(self.all_assets(nid)) - set(self.invalid_assets)

    def assets_amount(self, nid):
        return len(self.all_assets(nid))

    def valid_assets_amount(self, nid):
        return len(self.all_valid_assets(nid))

    @staticmethod
    def copy_node(node):
        new_node = deepcopy(node)
        new_node.fpointer = None
        return new_node

    def safe_add_ancestors(self, node, ancestors):
        # 如果没有祖先节点，那么添加该节点, 父节点是root node
        if len(ancestors) == 0:
            parent = self.root_node()
        else:
            parent = ancestors[0]

        # 如果当前节点已再树中，则移动当前节点到父节点中
        # 这个是由于 当前节点放到了二级节点中
        if not self.contains(parent.identifier):
            # logger.debug('Add parent: {}'.format(parent.identifier))
            self.safe_add_ancestors(parent, ancestors[1:])

        if self.contains(node.identifier):
            # msg = 'Move node to parent: {} => {}'.format(
            #     node.identifier, parent.identifier
            # )
            # logger.debug(msg)
            self.move_node(node.identifier, parent.identifier)
        else:
            # logger.debug('Add node: {}'.format(node.identifier))
            self.add_node(node, parent)
    #
    # def __getstate__(self):
    #     self.mutex = None
    #     self.all_nodes_assets_map = {}
    #     self.nodes_assets_map = {}
    #     return self.__dict__

    # def __setstate__(self, state):
    #     self.__dict__ = state
