from django.db import models
from django.utils.translation import gettext_lazy as _
from common.db.models import IncludesTextChoicesMeta
from common.tree import TreeNode


__all__ = [
    'Category', 'HostTypes', 'NetworkTypes', 'DatabaseTypes',
    'WebTypes', 'CloudTypes', 'Protocol', 'AllTypes',
]


class PlatformMixin:
    @classmethod
    def platform_constraints(cls):
        return {
            'has_domain': False,
            'has_su': False,
            'has_ping': False,
            'has_change_password': False,
            'has_verify_account': False,
            'has_create_account': False,
            '_protocols': []
        }


class Category(PlatformMixin, models.TextChoices):
    HOST = 'host', _('Host')
    NETWORK = 'network', _("NetworkDevice")
    DATABASE = 'database', _("Database")
    CLOUD = 'cloud', _("Clouding")
    WEB = 'web', _("Web")

    @classmethod
    def platform_constraints(cls) -> dict:
        return {
            cls.HOST: {
                'has_domain': True,
                'has_ping': True,
                'has_verify_account': True,
                'has_change_password': True,
                'has_create_account': True,
                '_protocols': ['ssh', 'telnet']
            },
            cls.NETWORK: {
                'has_domain': True,
                '_protocols': ['ssh', 'telnet']
            },
            cls.DATABASE: {
                'has_domain': True,
            },
            cls.WEB: {
                'has_domain': False,
                '_protocols': []
            },
            cls.CLOUD: {
                'has_domain': False,
                '_protocols': []
            }
        }


class HostTypes(PlatformMixin, models.TextChoices):
    LINUX = 'linux', 'Linux'
    WINDOWS = 'windows', 'Windows'
    UNIX = 'unix', 'Unix'
    BSD = 'bsd', 'BSD'
    MACOS = 'macos', 'MacOS'
    MAINFRAME = 'mainframe', _("Mainframe")
    OTHER_HOST = 'other_host', _("Other host")

    @classmethod
    def platform_constraints(cls):
        return {
            cls.LINUX: {
                '_protocols': ['ssh', 'rdp', 'vnc', 'telnet']
            },
            cls.WINDOWS: {
                '_protocols': ['ssh', 'rdp', 'vnc']
            },
            cls.MACOS: {
                '_protocols': ['ssh', 'vnc']
            }
        }


class NetworkTypes(PlatformMixin, models.TextChoices):
    SWITCH = 'switch', _("Switch")
    ROUTER = 'router', _("Router")
    FIREWALL = 'firewall', _("Firewall")
    OTHER_NETWORK = 'other_network', _("Other device")


class DatabaseTypes(PlatformMixin, models.TextChoices):
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
                'protocols': [name]
            }
        return meta


class WebTypes(PlatformMixin, models.TextChoices):
    General = 'general', 'General'


class CloudTypes(PlatformMixin, models.TextChoices):
    K8S = 'k8s', 'Kubernetes'


class AllTypes(metaclass=IncludesTextChoicesMeta):
    choices: list
    includes = [
        HostTypes, NetworkTypes, DatabaseTypes,
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
            (Category.NETWORK, NetworkTypes),
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


class Protocol(models.TextChoices):
    ssh = 'ssh', 'SSH'
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

            cls.k8s: 0
        }

