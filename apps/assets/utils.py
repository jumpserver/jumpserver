# ~*~ coding: utf-8 ~*~
#
from functools import reduce
from treelib import Tree
from collections import defaultdict
from copy import deepcopy
import threading
from django.db.models import Q

from common.utils import get_object_or_none, get_logger, timeit
from .models import SystemUser, Label, Asset


logger = get_logger(__file__)


def get_system_user_by_name(name):
    system_user = get_object_or_none(SystemUser, name=name)
    return system_user


def get_system_user_by_id(id):
    system_user = get_object_or_none(SystemUser, id=id)
    return system_user


class TreeService(Tree):
    tag_sep = ' / '

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes_assets_map = defaultdict(set)
        self.all_nodes_assets_map = {}

    @classmethod
    @timeit
    def new(cls):
        from .models import Node
        from orgs.utils import tmp_to_root_org

        with tmp_to_root_org():
            all_nodes = list(Node.objects.all().values("key", "value"))
            all_nodes.sort(key=lambda x: len(x["key"].split(":")))
            tree = cls()
            tree.create_node(tag='', identifier='')
            for node in all_nodes:
                key = node["key"]
                value = node["value"]
                parent_key = ":".join(key.split(":")[:-1])
                tree.create_node(
                    tag=value, identifier=key,
                    parent=parent_key,
                )
            tree.init_assets()
        return tree

    def init_assets_async(self):
        t = threading.Thread(target=self.init_assets)
        t.start()

    def init_assets(self):
        from orgs.utils import tmp_to_root_org
        self.all_nodes_assets_map = {}
        self.nodes_assets_map = defaultdict(set)
        logger.debug('Init tree assets')
        with tmp_to_root_org():
            queryset = Asset.objects.all().values_list('id', 'nodes__key')
            for asset_id, key in queryset:
                if not key:
                    continue
                self.nodes_assets_map[key].add(asset_id)

    def all_children_ids(self, nid, with_self=True):
        children_ids = self.expand_tree(nid)
        if not with_self:
            next(children_ids)
        return list(children_ids)

    def all_children(self, nid, with_self=True, deep=False):
        children_ids = self.all_children_ids(nid, with_self=with_self)
        return [self.get_node(i, deep=deep) for i in children_ids]

    def ancestors(self, nid, with_self=False, deep=False):
        ancestor_ids = list(self.rsearch(nid))
        ancestor_ids.pop()
        if not with_self:
            ancestor_ids.pop(0)
        return [self.get_node(i, deep=deep) for i in ancestor_ids]

    def get_node_full_tag(self, nid):
        ancestors = self.ancestors(nid, with_self=True)
        ancestors.reverse()
        return self.tag_sep.join([n.tag for n in ancestors])

    def get_family(self, nid, deep=False):
        ancestors = self.ancestors(nid, with_self=False, deep=deep)
        children = self.all_children(nid, with_self=False)
        return ancestors + [self[nid]] + children

    def root_node(self):
        return self.get_node(self.root)

    def get_node(self, nid, deep=False):
        node = super().get_node(nid)
        if deep:
            node = self.copy_node(node)
        return node

    def parent(self, nid, deep=False):
        parent = super().parent(nid)
        if deep:
            parent = self.copy_node(parent)
        return parent

    def assets(self, nid):
        assets = self.nodes_assets_map[nid]
        return assets

    def set_assets(self, nid, assets):
        self.nodes_assets_map[nid] = assets

    def all_assets(self, nid):
        assets = self.all_nodes_assets_map.get(nid)
        if assets:
            return assets
        assets = set(self.assets(nid))
        children = self.children(nid)
        for child in children:
            assets.update(self.all_assets(child.identifier))
        return assets

    def assets_amount(self, nid):
        return len(self.all_assets(nid))

    @staticmethod
    def copy_node(node):
        new_node = deepcopy(node)
        new_node.fpointer = None
        return new_node

    def safe_add_ancestors(self, ancestors):
        # 如果祖先节点为1个，那么添加该节点, 父节点是root node
        if len(ancestors) == 1:
            node = ancestors[0]
            parent = self.root_node()
        else:
            node, ancestors = ancestors[0], ancestors[1:]
            parent_id = ancestors[0].identifier
            # 如果父节点不存在, 则先添加父节点
            if not self.contains(parent_id):
                self.safe_add_ancestors(ancestors)
            parent = self.get_node(parent_id)

        # 如果当前节点已再树中，则移动当前节点到父节点中
        # 这个是由于 当前节点放到了二级节点中
        if self.contains(node.identifier):
            self.move_node(node.identifier, parent.identifier)
        else:
            self.add_node(node, parent)
    #
    # def __getstate__(self):
    #     self.mutex = None
    #     return self.__dict__
    #
    # def __setstate__(self, state):
    #     self.__dict__ = state
    #     self.mutex = threading.Lock()
