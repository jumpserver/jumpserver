from common.db.models import IncludesTextChoicesMeta, ChoicesMixin
from common.tree import TreeNode

from .category import Category
from .host import HostTypes
from .device import DeviceTypes
from .database import DatabaseTypes
from .web import WebTypes
from .cloud import CloudTypes


class AllTypes(ChoicesMixin, metaclass=IncludesTextChoicesMeta):
    choices: list
    includes = [
        HostTypes, DeviceTypes, DatabaseTypes,
        WebTypes, CloudTypes
    ]

    @classmethod
    def get_constraints(cls, category, tp):
        constraints = ConstrainMixin.platform_constraints()
        category_constraints = Category.platform_constraints().get(category) or {}
        constraints.update(category_constraints)

        types_cls = dict(cls.category_types()).get(category)
        if not types_cls:
            return constraints
        type_constraints = types_cls.platform_constraints().get(tp) or {}
        constraints.update(type_constraints)

        _protocols = constraints.pop('_protocols', [])
        default_ports = Protocol.default_ports()
        protocols = []
        for p in _protocols:
            port = default_ports.get(p, 0)
            protocols.append({'name': p, 'port': port})
        constraints['protocols'] = protocols
        return constraints

    @classmethod
    def category_types(cls):
        return (
            (Category.HOST, HostTypes),
            (Category.DEVICE, DeviceTypes),
            (Category.DATABASE, DatabaseTypes),
            (Category.WEB, WebTypes),
            (Category.CLOUD, CloudTypes)
        )

    @classmethod
    def grouped_choices(cls):
        grouped_types = [(str(ca), tp.choices) for ca, tp in cls.category_types()]
        return grouped_types

    @classmethod
    def grouped_choices_to_objs(cls):
        choices = cls.serialize_to_objs(Category.choices)
        mapper = dict(cls.grouped_choices())
        for choice in choices:
            children = cls.serialize_to_objs(mapper[choice['value']])
            choice['children'] = children
        return choices

    @staticmethod
    def serialize_to_objs(choices):
        title = ['value', 'display_name']
        return [dict(zip(title, choice)) for choice in choices]

    @staticmethod
    def choice_to_node(choice, pid, opened=True, is_parent=True, meta=None):
        node = TreeNode(**{
            'id': choice.name,
            'name': choice.label,
            'title': choice.label,
            'pId': pid,
            'open': opened,
            'isParent': is_parent,
        })
        if meta:
            node.meta = meta
        return node

    @classmethod
    def to_tree_nodes(cls):
        root = TreeNode(id='ROOT', name='类型节点', title='类型节点')
        nodes = [root]
        for category, types in cls.category_types():
            category_node = cls.choice_to_node(category, 'ROOT', meta={'type': 'category'})
            nodes.append(category_node)
            for tp in types:
                tp_node = cls.choice_to_node(tp, category_node.id, meta={'type': 'type'})
                nodes.append(tp_node)
        return nodes
