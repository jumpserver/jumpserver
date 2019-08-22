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


class LabelFilterMixin:
    def get_filter_labels_ids(self):
        query_params = self.request.query_params
        query_keys = query_params.keys()
        all_label_keys = Label.objects.values_list('name', flat=True)
        valid_keys = set(all_label_keys) & set(query_keys)

        if not valid_keys:
            return []

        labels_query = [
            {"name": key, "value": query_params[key]}
            for key in valid_keys
        ]
        args = [Q(**kwargs) for kwargs in labels_query]
        args = reduce(lambda x, y: x | y, args)
        labels_id = Label.objects.filter(args).values_list('id', flat=True)
        return labels_id


class LabelFilter(LabelFilterMixin):
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        labels_ids = self.get_filter_labels_ids()
        if not labels_ids:
            return queryset
        for labels_id in labels_ids:
            queryset = queryset.filter(labels=labels_id)
        return queryset


class TreeService(Tree):
    tag_sep = ' / '
    cache_key = '_NODE_FULL_TREE'
    cache_time = 3600

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes_assets_map = defaultdict(set)
        self.all_nodes_assets_map = {}
        self.mutex = threading.Lock()

    @classmethod
    @timeit
    def new(cls):
        from .models import Node
        from orgs.utils import get_current_org, set_to_root_org

        origin_org = get_current_org()
        set_to_root_org()
        all_nodes = Node.objects.all()
        origin_org.change_to()

        tree = cls()
        tree.create_node(tag='', identifier='')
        for node in all_nodes:
            tree.create_node(
                tag=node.value, identifier=node.key,
                parent=node.parent_key,
            )
        tree.init_assets_async()
        return tree

    def init_assets_async(self):
        t = threading.Thread(target=self.init_assets)
        t.start()

    def init_assets(self):
        from orgs.utils import get_current_org, set_to_root_org
        with self.mutex:
            origin_org = get_current_org()
            set_to_root_org()
            queryset = Asset.objects.all().valid().values_list('id', 'nodes__key')

            if origin_org:
                origin_org.change_to()
            for asset_id, key in queryset:
                if not key:
                    continue
                self.nodes_assets_map[key].add(asset_id)

    def all_children(self, nid, with_self=True, deep=False):
        children_ids = self.expand_tree(nid)
        if not with_self:
            next(children_ids)
        return [self.get_node(i, deep=deep) for i in children_ids]

    def ancestors(self, nid, with_self=False, deep=False):
        ancestor_ids = list(self.rsearch(nid))
        ancestor_ids.pop()
        if not with_self:
            ancestor_ids.pop(0)
        return [self.get_node(i, deep=deep) for i in ancestor_ids]

    def get_node_full_tag(self, nid):
        ancestors = self.ancestors(nid)
        ancestors.reverse()
        return self.tag_sep.join(n.tag for n in ancestors)

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
        with self.mutex:
            assets = self.nodes_assets_map[nid]
            return assets

    def set_assets(self, nid, assets):
        with self.mutex:
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

        print("Add node: {} {}".format(node.identifier, parent.identifier))
        # 如果当前节点已再树中，则移动当前节点到父节点中
        # 这个是由于 当前节点放到了二级节点中
        if self.contains(node.identifier):
            self.move_node(node.identifier, parent.identifier)
        else:
            self.add_node(node, parent)


