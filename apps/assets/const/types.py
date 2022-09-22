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
        CloudTypes, WebTypes,
    ]
    _category_constrains = {}

    @classmethod
    def get_constraints(cls, category, tp):
        types_cls = dict(cls.category_types()).get(category)
        if not types_cls:
            return {}
        type_constraints = types_cls.get_constrains()
        constraints = type_constraints.get(tp, {})
        cls.set_automation_methods(category, tp, constraints)
        return constraints

    @classmethod
    def set_automation_methods(cls, category, tp, constraints):
        from assets.playbooks import filter_platform_methods
        automation = constraints.get('automation', {})
        automation_methods = {}
        for item, enabled in automation.items():
            if not enabled:
                continue
            item_name = item.replace('_enabled', '')
            methods = filter_platform_methods(category, tp, item_name)
            methods = [{'name': m['name'], 'id': m['id']} for m in methods]
            automation_methods[item_name+'_methods'] = methods
        automation.update(automation_methods)
        constraints['automation'] = automation
        return constraints

    @classmethod
    def types(cls, with_constraints=True):
        types = []
        for category, tps in cls.category_types():
            types.extend([cls.serialize_type(category, tp, with_constraints) for tp in tps])
        return types

    @classmethod
    def categories(cls, with_constraints=True):
        categories = []
        for category, tps in cls.category_types():
            category_data = {
                'value': category.value,
                'label': category.label,
                'types': [cls.serialize_type(category, tp, with_constraints) for tp in tps]
            }
            categories.append(category_data)
        return categories

    @classmethod
    def serialize_type(cls, category, tp, with_constraints=True):
        data = {
            'value': tp.value,
            'label': tp.label,
            'category': category,
        }

        if with_constraints:
            data['constraints'] = cls.get_constraints(category, tp)
        else:
            data['constraints'] = []
        return data

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

    @classmethod
    def category_types(cls):
        return (
            (Category.HOST, HostTypes),
            (Category.DEVICE, DeviceTypes),
            (Category.DATABASE, DatabaseTypes),
            (Category.WEB, WebTypes),
            (Category.CLOUD, CloudTypes)
        )

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

    @classmethod
    def get_type_default_platform(cls, category, tp):
        constraints = cls.get_constraints(category, tp)
        data = {
            'name': tp.label, 'category': category.value,
            'type': tp.value, 'internal': True,
            'charset': constraints.get('charset', 'utf-8'),
            'domain_enabled': constraints.get('domain_enabled', False),
            'su_enabled': constraints.get('su_enabled', False),
        }
        if data['su_enabled'] and data.get('su_methods'):
            data['su_method'] = data['su_methods'][0]['id']

        protocols = constraints.get('protocols', [])
        for p in protocols:
            p.pop('secret_types', None)
        data['protocols'] = protocols

        automation = constraints.get('automation', {})
        enable_fields = {k: v for k, v in automation.items() if k.endswith('_enabled')}
        for k, v in enable_fields.items():
            auto_item = k.replace('_enabled', '')
            methods = automation.pop(auto_item + '_methods', [])
            if methods:
                automation[auto_item + '_method'] = methods[0]['id']
        data['automation'] = automation
        return data

    @classmethod
    def create_or_update_internal_platforms(cls):
        from assets.models import Platform
        for category, type_cls in cls.category_types():
            data = type_cls.internal_platforms()
            for tp, platform_datas in data.items():
                for d in platform_datas:
                    platform_data = {
                        **d, 'category': category.value, 'type': tp.value,
                        'internal': True, 'charset': 'utf-8'
                    }


