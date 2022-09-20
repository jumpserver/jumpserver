from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import IncludesTextChoicesMeta, ChoicesMixin
from common.tree import TreeNode


__all__ = [
    'Category', 'HostTypes', 'DeviceTypes', 'DatabaseTypes',
    'WebTypes', 'CloudTypes', 'Protocol', 'AllTypes',
]


class PlatformMixin:
    @classmethod
    def platform_constraints(cls):
        return {
            'domain_enabled': False,
            'su_enabled': False,
            'brand_enabled': False,
            'ping_enabled': False,
            'gather_facts_enabled': False,
            'change_password_enabled': False,
            'verify_account_enabled': False,
            'create_account_enabled': False,
            'gather_accounts_enabled': False,
            '_protocols': []
        }


class Category(PlatformMixin, ChoicesMixin, models.TextChoices):
    HOST = 'host', _('Host')
    DEVICE = 'device', _("Device")
    DATABASE = 'database', _("Database")
    CLOUD = 'cloud', _("Cloud service")
    WEB = 'web', _("Web")

    @classmethod
    def platform_constraints(cls) -> dict:
        return {
            cls.HOST: {
                'domain_enabled': True,
                'su_enabled': True, 'su_method': 'sudo',
                'ping_enabled': True, 'ping_method': 'ping',
                'gather_facts_enabled': True, 'gather_facts_method': 'gather_facts_posix',
                'verify_account_enabled': True, 'verify_account_method': 'verify_account_posix',
                'change_password_enabled': True, 'change_password_method': 'change_password_posix',
                'create_account_enabled': True, 'create_account_method': 'create_account_posix',
                'gather_accounts_enabled': True, 'gather_accounts_method': 'gather_accounts_posix',
                '_protocols': ['ssh', 'telnet'],
            },
            cls.DEVICE: {
                'domain_enabled': True,
                'brand_enabled': True,
                'brands': [
                    ('huawei', 'Huawei'),
                    ('cisco', 'Cisco'),
                    ('juniper', 'Juniper'),
                    ('h3c', 'H3C'),
                    ('dell', 'Dell'),
                    ('other', 'Other'),
                ],
                'su_enabled': False,
                'ping_enabled': True, 'ping_method': 'ping',
                'gather_facts_enabled': False,
                'verify_account_enabled': False,
                'change_password_enabled': False,
                'create_account_enabled': False,
                'gather_accounts_enabled': False,
                '_protocols': ['ssh', 'telnet']
            },
            cls.DATABASE: {
                'domain_enabled': True,
                'su_enabled': False,
                'gather_facts_enabled': True,
                'verify_account_enabled': True,
                'change_password_enabled': True,
                'create_account_enabled': True,
                'gather_accounts_enabled': True,
                '_protocols': []
            },
            cls.WEB: {
                'domain_enabled': False,
                'su_enabled': False,
                'ping_enabled': False,
                'gather_facts_enabled': False,
                'verify_account_enabled': False,
                'change_password_enabled': False,
                'create_account_enabled': False,
                'gather_accounts_enabled': False,
                '_protocols': ['http', 'https']
            },
            cls.CLOUD: {
                'domain_enabled': False,
                'su_enabled': False,
                'ping_enabled': False,
                'gather_facts_enabled': False,
                'verify_account_enabled': False,
                'change_password_enabled': False,
                'create_account_enabled': False,
                'gather_accounts_enabled': False,
                '_protocols': []
            }
        }


class HostTypes(PlatformMixin, ChoicesMixin, models.TextChoices):
    LINUX = 'linux', 'Linux'
    WINDOWS = 'windows', 'Windows'
    UNIX = 'unix', 'Unix'
    OTHER_HOST = 'other', _("Other")

    @classmethod
    def platform_constraints(cls):
        return {
            cls.LINUX: {
                '_protocols': ['ssh', 'rdp', 'vnc', 'telnet']
            },
            cls.WINDOWS: {
                'gather_facts_method': 'gather_facts_windows',
                'verify_account_method': 'verify_account_windows',
                'change_password_method': 'change_password_windows',
                'create_account_method': 'create_account_windows',
                'gather_accounts_method': 'gather_accounts_windows',
                '_protocols': ['rdp', 'ssh', 'vnc'],
                'su_enabled': False
            },
            cls.UNIX: {
                '_protocols': ['ssh', 'vnc']
            }
        }


class DeviceTypes(PlatformMixin, ChoicesMixin, models.TextChoices):
    GENERAL = 'general', _("General device")
    SWITCH = 'switch', _("Switch")
    ROUTER = 'router', _("Router")
    FIREWALL = 'firewall', _("Firewall")


class DatabaseTypes(PlatformMixin, ChoicesMixin, models.TextChoices):
    MYSQL = 'mysql', 'MySQL'
    MARIADB = 'mariadb', 'MariaDB'
    POSTGRESQL = 'postgresql', 'PostgreSQL'
    ORACLE = 'oracle', 'Oracle'
    SQLSERVER = 'sqlserver', 'SQLServer'
    MONGODB = 'mongodb', 'MongoDB'
    REDIS = 'redis', 'Redis'

    @classmethod
    def platform_constraints(cls):
        meta = {}
        for name, label in cls.choices:
            meta[name] = {
                '_protocols': [name],
                'gather_facts_method': f'gather_facts_{name}',
                'verify_account_method': f'verify_account_{name}',
                'change_password_method': f'change_password_{name}',
                'create_account_method': f'create_account_{name}',
                'gather_accounts_method': f'gather_accounts_{name}',
            }
        return meta


class WebTypes(PlatformMixin, ChoicesMixin, models.TextChoices):
    WEBSITE = 'website', _('General website')


class CloudTypes(PlatformMixin, ChoicesMixin, models.TextChoices):
    K8S = 'k8s', 'Kubernetes'

    @classmethod
    def platform_constraints(cls):
        return {
            cls.K8S: {
                '_protocols': ['k8s']
            }
        }


class AllTypes(ChoicesMixin, metaclass=IncludesTextChoicesMeta):
    choices: list
    includes = [
        HostTypes, DeviceTypes, DatabaseTypes,
        WebTypes, CloudTypes
    ]

    @classmethod
    def get_constraints(cls, category, tp):
        constraints = PlatformMixin.platform_constraints()
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
        title = ['value', 'label']
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


class Protocol(ChoicesMixin, models.TextChoices):
    ssh = 'ssh', 'SSH'
    sftp = 'sftp', 'SFTP'
    rdp = 'rdp', 'RDP'
    telnet = 'telnet', 'Telnet'
    vnc = 'vnc', 'VNC'

    mysql = 'mysql', 'MySQL'
    mariadb = 'mariadb', 'MariaDB'
    oracle = 'oracle', 'Oracle'
    postgresql = 'postgresql', 'PostgreSQL'
    sqlserver = 'sqlserver', 'SQLServer'
    redis = 'redis', 'Redis'
    mongodb = 'mongodb', 'MongoDB'

    k8s = 'k8s', 'K8S'
    http = 'http', 'HTTP'
    https = 'https', 'HTTPS'

    @classmethod
    def host_protocols(cls):
        return [cls.ssh, cls.rdp, cls.telnet, cls.vnc]

    @classmethod
    def db_protocols(cls):
        return [
            cls.mysql, cls.mariadb, cls.postgresql, cls.oracle,
            cls.sqlserver, cls.redis, cls.mongodb,
        ]

    @classmethod
    def default_ports(cls):
        return {
            cls.ssh: 22,
            cls.sftp: 22,
            cls.rdp: 3389,
            cls.vnc: 5900,
            cls.telnet: 21,

            cls.mysql: 3306,
            cls.mariadb: 3306,
            cls.postgresql: 5432,
            cls.oracle: 1521,
            cls.sqlserver: 1433,
            cls.mongodb: 27017,
            cls.redis: 6379,

            cls.k8s: 0,

            cls.http: 80,
            cls.https: 443
        }

