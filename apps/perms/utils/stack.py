# -*- coding: utf-8 -*-
#
import re
from collections import defaultdict
from common.struct import Stack
from assets.utils import NodeUtil


class PermStackUtilMixin:
    def __init__(self, debug=False):
        self.stack = None
        self._nodes = {}
        self._debug = debug

    @staticmethod
    def sorted_by(node_dict):
        return [int(i) for i in node_dict['key'].split(':')]

    @staticmethod
    def is_children(item1, item2):
        key1 = item1["key"]
        key2 = item2["key"]
        return key2.startswith(key1 + ':') and (
            len(key2.split(':')) - len(key1.split(':'))
        ) == 1

    def debug(self, msg):
        self._debug and print(msg)


class PermSystemUserNodeUtil(PermStackUtilMixin):
    def get_nodes_family_and_system_users(self, nodes_with_system_users):
        node_util = NodeUtil()
        _nodes_keys = nodes_with_system_users.keys()
        family_keys = node_util.get_some_nodes_family_keys_by_keys(_nodes_keys)

        nodes_items = []
        for i in family_keys:
            system_users = nodes_with_system_users.get(i, defaultdict(int))
            item = {"key": i, "system_users": system_users}
            nodes_items.append(item)
        nodes_items.sort(key=self.sorted_by)
        nodes_items.append({"key": "", "system_users": defaultdict(int)})

        self.stack = Stack()
        for item in nodes_items:
            self.debug("准备: {} 栈顶: {}".format(
                item['key'], self.stack.top["key"] if self.stack.top else None)
            )
            # 入栈之前检查，该节点是不是栈顶节点的子节点
            # 如果不是，则栈顶出栈
            while self.stack.top and not self.is_children(self.stack.top, item):
                self.pop_from_stack_system_users()
            self.push_to_stack_system_users(item)
        # 出栈最后一个
        self.debug("剩余: {}".format(', '.join([n["key"] for n in self.stack])))
        return self._nodes

    def push_to_stack_system_users(self, item):
        # 入栈之前检查
        # 如果栈是空的，证明是一颗树的根部
        if not self.stack.is_empty():
            # 如果不是根节点,
            # 该节点的祖先应该是父节点的祖先加上父节点
            # 该节点的名字是父节点的名字+自己的名字
            item_system_users = item["system_users"]
            for system_user, action in self.stack.top["system_users"].items():
                item_system_users[system_user] |= action
            item["system_users"] = item_system_users
        self.debug("入栈: {}".format(item['key']))
        self.stack.push(item)

    # 出栈
    def pop_from_stack_system_users(self):
        _node = self.stack.pop()
        self._nodes[_node["key"]] = _node["system_users"]
        self.debug("出栈: {} 栈顶: {}".format(_node['key'], self.stack.top['key'] if self.stack.top else None))


class PermAssetsAmountUtil(PermStackUtilMixin):
    def push_to_stack_nodes_amount(self, item):
        self.debug("入栈: {}".format(item['key']))
        self.stack.push(item)

    def pop_from_stack_nodes_amount(self):
        _node = self.stack.pop()
        self.debug("出栈: {} 栈顶: {}".format(
            _node['key'], self.stack.top['key'] if self.stack.top else None)
        )
        _node["assets_amount"] = len(_node["all_assets"] | _node["assets"])
        self._nodes[_node.pop("key")] = _node

        if not self.stack.top:
            return
        self.stack.top["all_assets"]\
            .update(_node["all_assets"] | _node["assets"])

    def compute_nodes_assets_amount(self, nodes_with_assets):
        self.stack = Stack()
        nodes_items = []
        for key, values in nodes_with_assets.items():
            nodes_items.append({
                "key": key, "assets": values["assets"],
                "all_assets": values["all_assets"], "assets_amount": 0
            })

        nodes_items.sort(key=self.sorted_by)
        nodes_items.append({"key": "", "assets": set(), "all_assets": set(), "assets_amount": 0})
        self.stack = Stack()
        for item in nodes_items:
            self.debug("准备: {} 栈顶: {}".format(
                item['key'], self.stack.top["key"] if self.stack.top else None)
            )
            # 入栈之前检查，该节点是不是栈顶节点的子节点
            # 如果不是，则栈顶出栈
            while self.stack.top and not self.is_children(self.stack.top, item):
                self.pop_from_stack_nodes_amount()
            self.push_to_stack_nodes_amount(item)
        # 出栈最后一个
        self.debug("剩余: {}".format(', '.join([n["key"] for n in self.stack])))
        return self._nodes