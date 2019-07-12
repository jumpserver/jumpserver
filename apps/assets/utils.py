# ~*~ coding: utf-8 ~*~
#
import time
from functools import reduce
from django.db.models import Prefetch, Q

from common.utils import get_object_or_none, get_logger
from common.struct import Stack
from .models import SystemUser, Label, Node, Asset


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


class NodeUtil:
    def __init__(self, with_assets_amount=False, debug=False):
        self.stack = Stack()
        self._nodes = {}
        self.with_assets_amount = with_assets_amount
        self._debug = debug
        self.init()

    @staticmethod
    def sorted_by(node):
        return [int(i) for i in node.key.split(':')]

    def get_queryset(self):
        all_nodes = Node.objects.all()
        if self.with_assets_amount:
            all_nodes = all_nodes.prefetch_related(
                Prefetch('assets', queryset=Asset.objects.all().only('id'))
            )
            all_nodes = list(all_nodes)
            for node in all_nodes:
                node._assets = set(node.assets.all())
        return all_nodes

    def get_all_nodes(self):
        all_nodes = sorted(self.get_queryset(), key=self.sorted_by)

        guarder = Node(key='', value='Guarder')
        guarder._assets = []
        all_nodes.append(guarder)
        return all_nodes

    def push_to_stack(self, node):
        # 入栈之前检查
        # 如果栈是空的，证明是一颗树的根部
        if self.stack.is_empty():
            node._full_value = node.value
            node._parents = []
        else:
            # 如果不是根节点,
            # 该节点的祖先应该是父节点的祖先加上父节点
            # 该节点的名字是父节点的名字+自己的名字
            node._parents = [self.stack.top] + self.stack.top._parents
            node._full_value = ' / '.join(
                [self.stack.top._full_value, node.value]
            )
        node._children = []
        node._all_children = []
        self.debug("入栈: {}".format(node.key))
        self.stack.push(node)

    # 出栈
    def pop_from_stack(self):
        _node = self.stack.pop()
        self.debug("出栈: {} 栈顶: {}".format(_node.key, self.stack.top.key if self.stack.top else None))
        self._nodes[_node.key] = _node
        if not self.stack.top:
            return
        if self.with_assets_amount:
            self.stack.top._assets.update(_node._assets)
            _node._assets_amount = len(_node._assets)
            delattr(_node, '_assets')
        self.stack.top._children.append(_node)
        self.stack.top._all_children.extend([_node] + _node._all_children)

    def init(self):
        all_nodes = self.get_all_nodes()
        for node in all_nodes:
            self.debug("准备: {} 栈顶: {}".format(node.key, self.stack.top.key if self.stack.top else None))
            # 入栈之前检查，该节点是不是栈顶节点的子节点
            # 如果不是，则栈顶出栈
            while self.stack.top and not self.stack.top.is_children(node):
                self.pop_from_stack()
            self.push_to_stack(node)
        # 出栈最后一个
        self.debug("剩余: {}".format(', '.join([n.key for n in self.stack])))

    def get_nodes_by_queryset(self, queryset):
        nodes = []
        for n in queryset:
            node = self.get_node_by_key(n.key)
            if not node:
                continue
            nodes.append(node)
        return nodes

    def get_node_by_key(self, key):
        return self._nodes.get(key)

    def debug(self, msg):
        self._debug and logger.debug(msg)

    def set_assets_amount(self):
        for node in self._nodes.values():
            node.assets_amount = node._assets_amount

    def set_full_value(self):
        for node in self._nodes.values():
            node.full_value = node._full_value

    @property
    def nodes(self):
        return list(self._nodes.values())

    def get_family_by_key(self, key):
        tree_nodes = set()
        node = self.get_node_by_key(key)
        if not node:
            return []
        tree_nodes.update(node._parents)
        tree_nodes.add(node)
        tree_nodes.update(node._all_children)
        return list(tree_nodes)

    # 使用给定节点生成一颗树
    # 找到他们的祖先节点
    # 可选找到他们的子孙节点
    def get_family(self, node):
        return self.get_family_by_key(node.key)

    def get_family_keys_by_key(self, key):
        nodes = self.get_family_by_key(key)
        return [n.key for n in nodes]

    def get_some_nodes_family_by_keys(self, keys):
        family = set()
        for key in keys:
            family.update(self.get_family_by_key(key))
        return family

    def get_some_nodes_family_keys_by_keys(self, keys):
        family = self.get_some_nodes_family_by_keys(keys)
        return [n.key for n in family]

    def get_nodes_parents_by_key(self, key, with_self=True):
        parents = set()
        node = self.get_node_by_key(key)
        if not node:
            return []
        parents.update(set(node._parents))
        if with_self:
            parents.add(node)
        return list(parents)

    def get_node_parents(self, node, with_self=True):
        return self.get_nodes_parents_by_key(node.key, with_self=with_self)

    def get_nodes_parents_keys_by_key(self, key, with_self=True):
        nodes = self.get_nodes_parents_by_key(key, with_self=with_self)
        return [n.key for n in nodes]

    def get_all_children_by_key(self, key, with_self=True):
        children = set()
        node = self.get_node_by_key(key)
        if not node:
            return []
        children.update(set(node._all_children))
        if with_self:
            children.add(node)
        return list(children)

    def get_children(self, node, with_self=True):
        return self.get_all_children_by_key(node.key, with_self=with_self)

    def get_children_keys_by_key(self, key, with_self=True):
        nodes = self.get_all_children_by_key(key, with_self=with_self)
        return [n.key for n in nodes]


def test_node_tree():
    tree = NodeUtil()
    for node in tree._nodes.values():
        print("Check {}".format(node.key))
        children_wanted = node.get_all_children().count()
        children = len(node._children)
        if children != children_wanted:
            print("{} children not equal: {} != {}".format(node.key, children, children_wanted))

        assets_amount_wanted = node.get_all_assets().count()
        if node._assets_amount != assets_amount_wanted:
            print("{} assets amount not equal: {} != {}".format(
                node.key, node._assets_amount, assets_amount_wanted)
            )

        full_value_wanted = node.full_value
        if node._full_value != full_value_wanted:
            print("{} full value not equal: {} != {}".format(
                node.key, node._full_value, full_value_wanted)
            )

        parents_wanted = node.get_ancestor().count()
        parents = len(node._parents)
        if parents != parents_wanted:
            print("{} parents count not equal: {} != {}".format(
                node.key, parents, parents_wanted)
            )






