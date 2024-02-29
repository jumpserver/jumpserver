import json
from collections import defaultdict
from copy import deepcopy

from django.conf import settings
from django.utils.translation import gettext as _

from common.db.models import ChoicesMixin
from jumpserver.utils import get_current_request
from .category import Category
from .cloud import CloudTypes
from .custom import CustomTypes
from .database import DatabaseTypes
from .device import DeviceTypes
from .gpt import GPTTypes
from .host import HostTypes
from .web import WebTypes


class AllTypes(ChoicesMixin):
    choices: list
    includes = [
        HostTypes, DeviceTypes, DatabaseTypes,
        CloudTypes, WebTypes, CustomTypes, GPTTypes
    ]
    _category_constrains = {}
    _automation_methods = None
    _current_language = settings.LANGUAGE_CODE

    @classmethod
    def choices(cls):
        choices = []
        for tp in cls.includes:
            choices.extend(tp.get_choices())
        return choices

    @classmethod
    def get_choices(cls):
        return cls.choices()

    @classmethod
    def filter_choices(cls, category):
        choices = dict(cls.category_types()).get(category, cls).get_choices()
        return choices() if callable(choices) else choices

    @classmethod
    def get_constraints(cls, category, tp_name):
        if not isinstance(tp_name, str):
            tp_name = tp_name.value

        types_cls = dict(cls.category_types()).get(category)
        if not types_cls:
            return {}
        type_constraints = types_cls.get_constrains()
        constraints = type_constraints.get(tp_name, {})
        cls.set_automation_methods(category, tp_name, constraints)
        return constraints

    @classmethod
    def get_primary_protocol_name(cls, category, tp):
        constraints = cls.get_constraints(category, tp)
        if not constraints:
            return None
        return constraints.get('protocols')[0]['name']

    @classmethod
    def get_automation_methods(cls):
        from assets.automations import methods as asset
        from accounts.automations import methods as account

        automation_methods = \
            asset.platform_automation_methods + \
            account.platform_automation_methods

        request = get_current_request()
        if request is None:
            return automation_methods

        language = request.LANGUAGE_CODE
        if cls._automation_methods is not None and language == cls._current_language:
            automation_methods = cls._automation_methods
        else:
            automation_methods = \
                asset.get_platform_automation_methods(asset.BASE_DIR, language) + \
                account.get_platform_automation_methods(account.BASE_DIR, language)

        cls._current_language = language
        cls._automation_methods = automation_methods
        return cls._automation_methods

    @classmethod
    def set_automation_methods(cls, category, tp_name, constraints):
        from assets.automations import filter_platform_methods, sorted_methods
        automation = constraints.get('automation', {})
        automation_methods = {}
        platform_automation_methods = cls.get_automation_methods()
        for item, enabled in automation.items():
            if not enabled:
                continue
            item_name = item.replace('_enabled', '')
            methods = filter_platform_methods(
                category, tp_name, item_name, methods=platform_automation_methods
            )
            methods = sorted_methods(methods)
            methods = [{'name': m['name'], 'id': m['id']} for m in methods]
            automation_methods[item_name + '_methods'] = methods
        automation.update(automation_methods)
        constraints['automation'] = automation
        return constraints

    @classmethod
    def types(cls, with_constraints=True):
        types = []
        for category, type_cls in cls.category_types():
            tps = type_cls.get_types()
            types.extend([cls.serialize_type(category, tp, with_constraints) for tp in tps])
        return types

    @classmethod
    def categories(cls, with_constraints=True):
        categories = []
        for category, type_cls in cls.category_types():
            tps = type_cls.get_types()
            if not tps:
                continue
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
        grouped_types = [(str(ca), tp.get_choices()) for ca, tp in cls.category_types()]
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
            (Category.CLOUD, CloudTypes),
            (Category.WEB, WebTypes),
            (Category.GPT, GPTTypes),
            (Category.CUSTOM, CustomTypes),
        )

    @classmethod
    def get_types(cls, exclude_custom=False):
        choices = []

        for name, tp in dict(cls.category_types()).items():
            if name == Category.CUSTOM and exclude_custom:
                continue
            choices.extend(tp.get_types())
        return choices

    @classmethod
    def get_types_values(cls, exclude_custom=False):
        choices = cls.get_types(exclude_custom=exclude_custom)
        return [c.value for c in choices]

    @staticmethod
    def choice_to_node(choice, pid, opened=True, is_parent=True, meta=None):
        node = {
            'id': pid + '_' + choice.name,
            'name': choice.label,
            'title': choice.label,
            'pId': pid,
            'open': opened,
            'isParent': is_parent,
        }
        if meta:
            node['meta'] = meta
        return node

    @classmethod
    def platform_to_node(cls, p, pid, include_asset):
        node = {
            'id': '{}'.format(p.id),
            'name': p.name,
            'title': p.name,
            'pId': pid,
            'isParent': include_asset,
            'meta': {
                'type': 'platform'
            }
        }
        return node

    @classmethod
    def asset_to_node(cls, asset, pid):
        node = {
            'id': '{}'.format(asset.id),
            'name': asset.name,
            'title': f'{asset.address}\n{asset.comment}',
            'pId': pid,
            'isParent': False,
            'open': False,
            'iconSkin': asset.type,
            'chkDisabled': not asset.is_active,
            'meta': {
                'type': 'platform',
                'data': {
                    'platform_type': asset.platform.type,
                    'org_name': asset.org_name,
                    # 'sftp': asset.platform_id in sftp_enabled_platform,
                    'name': asset.name,
                    'address': asset.address
                },
            }
        }
        return node

    @classmethod
    def get_root_nodes(cls):
        return dict(id='ROOT', name=_('All types'), title=_('All types'), open=True, isParent=True)

    @classmethod
    def get_tree_nodes(cls, resource_platforms, include_asset=False, get_root=True):
        from ..models import Platform
        platform_count = defaultdict(int)
        for platform_id in resource_platforms:
            platform_count[platform_id] += 1

        category_type_mapper = defaultdict(int)
        platforms = Platform.objects.all()
        tp_platforms = defaultdict(list)

        for p in platforms:
            category_type_mapper[p.category + '_' + p.type] += platform_count[p.id]
            category_type_mapper[p.category] += platform_count[p.id]
            tp_platforms[p.category + '_' + p.type].append(p)

        nodes = [cls.get_root_nodes()] if get_root else []
        for category, type_cls in cls.category_types():
            # Category 格式化
            meta = {'type': 'category', 'category': category.value, '_type': category.value}
            category_node = cls.choice_to_node(category, 'ROOT', meta=meta)
            category_count = category_type_mapper.get(category, 0)
            category_node['name'] += f' ({category_count})'
            nodes.append(category_node)

            # Type 格式化
            types = type_cls.get_types()
            for tp in types:
                meta = {'type': 'type', 'category': category.value, '_type': tp.value}
                tp_node = cls.choice_to_node(tp, category_node['id'], opened=False, meta=meta)
                tp_count = category_type_mapper.get(category + '_' + tp, 0)
                tp_node['name'] += f' ({tp_count})'
                platforms = tp_platforms.get(category + '_' + tp, [])
                if not platforms:
                    tp_node['isParent'] = False
                nodes.append(tp_node)

                # Platform 格式化
                for p in platforms:
                    platform_node = cls.platform_to_node(p, tp_node['id'], include_asset)
                    platform_node['name'] += f' ({platform_count.get(p.id, 0)})'
                    nodes.append(platform_node)
        return nodes

    @classmethod
    def to_tree_nodes(cls, include_asset, count_resource='asset'):
        from accounts.models import Account
        from ..models import Asset
        if count_resource == 'account':
            resource_platforms = Account.objects.all().values_list('asset__platform_id', flat=True)
        else:
            resource_platforms = Asset.objects.all().values_list('platform_id', flat=True)
        return cls.get_tree_nodes(resource_platforms, include_asset)

    @classmethod
    def get_type_default_platform(cls, category, tp):
        constraints = cls.get_constraints(category, tp)
        data = {
            'category': category,
            'type': tp, 'internal': True,
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
    def create_or_update_by_platform_data(cls, platform_data, platform_cls=None):
        # 不直接用 Platform 是因为可能在 migrations 中使用
        from assets.models import Platform
        if platform_cls is None:
            platform_cls = Platform

        automation_data = platform_data.pop('automation', {})
        protocols_data = platform_data.pop('protocols', [])

        name = platform_data['name']
        platform, created = platform_cls.objects.update_or_create(
            defaults=platform_data, name=name
        )
        if not platform.automation:
            automation = platform_cls.automation.field.related_model.objects.create()
            platform.automation = automation
            platform.save()
        else:
            automation = platform.automation
        for k, v in automation_data.items():
            setattr(automation, k, v)
        automation.save()

        platform.protocols.all().delete()
        for p in protocols_data:
            platform.protocols.create(**p)

    @classmethod
    def create_or_update_internal_platforms(cls, platform_cls=None):
        if platform_cls is None:
            platform_cls = cls

        # print("\n\tCreate internal platforms")
        for category, type_cls in cls.category_types():
            # print("\t## Category: {}".format(category.label))
            data = type_cls.internal_platforms()

            for tp, platform_datas in data.items():
                # print("\t  >> Type: {}".format(tp.label))
                default_platform_data = cls.get_type_default_platform(category, tp)
                default_automation = default_platform_data.pop('automation', {})
                default_protocols = default_platform_data.pop('protocols', [])

                for d in platform_datas:
                    name = d['name']
                    print("\t    - Platform: {}".format(name))
                    _automation = d.pop('automation', {})
                    _protocols = d.pop('_protocols', [])
                    _protocols_setting = d.pop('protocols_setting', {})

                    protocols_data = deepcopy(default_protocols)
                    if _protocols:
                        protocols_data = [p for p in protocols_data if p['name'] in _protocols]

                    for p in protocols_data:
                        setting = _protocols_setting.get(p['name'], {})
                        p['required'] = setting.pop('required', False)
                        p['default'] = setting.pop('default', False)
                        p['setting'] = {**p.get('setting', {}).get('default', ''), **setting}

                    platform_data = {
                        **default_platform_data, **d,
                        'automation': {**default_automation, **_automation},
                        'protocols': protocols_data
                    }
                    print(json.dumps(platform_data, indent=4))
                    # cls.create_or_update_by_platform_data(platform_data, platform_cls=platform_cls)

    @classmethod
    def update_user_create_platforms(cls, platform_cls):
        internal_platforms = []
        for category, type_cls in cls.category_types():
            data = type_cls.internal_platforms()
            for tp, platform_datas in data.items():
                for d in platform_datas:
                    internal_platforms.append(d['name'])

        user_platforms = platform_cls.objects.exclude(name__in=internal_platforms)
        for platform in user_platforms:
            print("\t- Update platform: {}".format(platform.name))
            platform_data = cls.get_type_default_platform(platform.category, platform.type)
            platform_data['name'] = platform.name
            cls.create_or_update_by_platform_data(platform_data, platform_cls=platform_cls)
        user_platforms.update(internal=False)
