#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

import uuid
import logging
import random
from functools import reduce
from collections import OrderedDict

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.fields.model import JsonDictTextField
from common.utils import lazyproperty
from orgs.mixins.models import OrgModelMixin, OrgManager
from .utils import Connectivity

__all__ = ['Asset', 'ProtocolsMixin', 'Platform']
logger = logging.getLogger(__name__)


def default_cluster():
    from .cluster import Cluster
    name = "Default"
    defaults = {"name": name}
    cluster, created = Cluster.objects.get_or_create(
        defaults=defaults, name=name
    )
    return cluster.id


def default_node():
    try:
        from .node import Node
        root = Node.org_root()
        return root
    except:
        return None


class AssetManager(OrgManager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            platform_base=models.F('platform__base')
        )


class AssetQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def valid(self):
        return self.active()

    def has_protocol(self, name):
        return self.filter(protocols__contains=name)


class ProtocolsMixin:
    protocols = ''
    PROTOCOL_SSH = 'ssh'
    PROTOCOL_RDP = 'rdp'
    PROTOCOL_TELNET = 'telnet'
    PROTOCOL_VNC = 'vnc'
    PROTOCOL_CHOICES = (
        (PROTOCOL_SSH, 'ssh'),
        (PROTOCOL_RDP, 'rdp'),
        (PROTOCOL_TELNET, 'telnet'),
        (PROTOCOL_VNC, 'vnc'),
    )

    @property
    def protocols_as_list(self):
        if not self.protocols:
            return []
        return self.protocols.split(' ')

    @property
    def protocols_as_dict(self):
        d = OrderedDict()
        protocols = self.protocols_as_list
        for i in protocols:
            if '/' not in i:
                continue
            name, port = i.split('/')[:2]
            if not all([name, port]):
                continue
            d[name] = int(port)
        return d

    @property
    def protocols_as_json(self):
        return [
            {"name": name, "port": port}
            for name, port in self.protocols_as_dict.items()
        ]

    def has_protocol(self, name):
        return name in self.protocols_as_dict

    @property
    def ssh_port(self):
        return self.protocols_as_dict.get("ssh", 22)


class NodesRelationMixin:
    NODES_CACHE_KEY = 'ASSET_NODES_{}'
    ALL_ASSET_NODES_CACHE_KEY = 'ALL_ASSETS_NODES'
    CACHE_TIME = 3600 * 24 * 7
    id = ""
    _all_nodes_keys = None

    def get_nodes(self):
        from .node import Node
        nodes = self.nodes.all()
        if not nodes:
            nodes = Node.objects.filter(id=Node.org_root().id)
        return nodes

    def get_all_nodes(self, flat=False):
        nodes = []
        for node in self.get_nodes():
            _nodes = node.get_ancestors(with_self=True)
            nodes.append(_nodes)
        if flat:
            nodes = list(reduce(lambda x, y: set(x) | set(y), nodes))
        return nodes


class Platform(models.Model):
    CHARSET_CHOICES = (
        ('utf8', 'UTF-8'),
        ('gbk', 'GBK'),
    )
    BASE_CHOICES = (
        ('Linux', 'Linux'),
        ('Unix', 'Unix'),
        ('MacOS', 'MacOS'),
        ('BSD', 'BSD'),
        ('Windows', 'Windows'),
        ('Other', 'Other'),
    )
    name = models.SlugField(verbose_name=_("Name"), unique=True, allow_unicode=True)
    base = models.CharField(choices=BASE_CHOICES, max_length=16, default='Linux', verbose_name=_("Base"))
    charset = models.CharField(default='utf8', choices=CHARSET_CHOICES, max_length=8, verbose_name=_("Charset"))
    meta = JsonDictTextField(blank=True, null=True, verbose_name=_("Meta"))
    internal = models.BooleanField(default=False, verbose_name=_("Internal"))
    comment = models.TextField(blank=True, null=True, verbose_name=_("Comment"))

    @classmethod
    def default(cls):
        linux, created = cls.objects.get_or_create(
            defaults={'name': 'Linux'}, name='Linux'
        )
        return linux.id

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Platform")
        # ordering = ('name',)


class Asset(ProtocolsMixin, NodesRelationMixin, OrgModelMixin):
    # Important
    PLATFORM_CHOICES = (
        ('Linux', 'Linux'),
        ('Unix', 'Unix'),
        ('MacOS', 'MacOS'),
        ('BSD', 'BSD'),
        ('Windows', 'Windows'),
        ('Windows2016', 'Windows(2016)'),
        ('Other', 'Other'),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    ip = models.CharField(max_length=128, verbose_name=_('IP'), db_index=True)
    hostname = models.CharField(max_length=128, verbose_name=_('Hostname'))
    protocol = models.CharField(max_length=128, default=ProtocolsMixin.PROTOCOL_SSH,
                                choices=ProtocolsMixin.PROTOCOL_CHOICES,
                                verbose_name=_('Protocol'))
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    protocols = models.CharField(max_length=128, default='ssh/22', blank=True, verbose_name=_("Protocols"))
    platform = models.ForeignKey(Platform, default=Platform.default, on_delete=models.PROTECT, verbose_name=_("Platform"), related_name='assets')
    domain = models.ForeignKey("assets.Domain", null=True, blank=True, related_name='assets', verbose_name=_("Domain"), on_delete=models.SET_NULL)
    nodes = models.ManyToManyField('assets.Node', default=default_node, related_name='assets', verbose_name=_("Nodes"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    # Auth
    admin_user = models.ForeignKey('assets.AdminUser', on_delete=models.PROTECT, null=True, verbose_name=_("Admin user"), related_name='assets')

    # Some information
    public_ip = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Public IP'))
    number = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Asset number'))

    # Collect
    vendor = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Vendor'))
    model = models.CharField(max_length=54, null=True, blank=True, verbose_name=_('Model'))
    sn = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Serial number'))

    cpu_model = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('CPU model'))
    cpu_count = models.IntegerField(null=True, verbose_name=_('CPU count'))
    cpu_cores = models.IntegerField(null=True, verbose_name=_('CPU cores'))
    cpu_vcpus = models.IntegerField(null=True, verbose_name=_('CPU vcpus'))
    memory = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Memory'))
    disk_total = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk total'))
    disk_info = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk info'))

    os = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('OS'))
    os_version = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('OS version'))
    os_arch = models.CharField(max_length=16, blank=True, null=True, verbose_name=_('OS arch'))
    hostname_raw = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Hostname raw'))

    labels = models.ManyToManyField('assets.Label', blank=True, related_name='assets', verbose_name=_("Labels"))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    objects = AssetManager.from_queryset(AssetQuerySet)()
    _connectivity = None

    def __str__(self):
        return '{0.hostname}({0.ip})'.format(self)

    @property
    def is_valid(self):
        warning = ''
        if not self.is_active:
            warning += ' inactive'
        if warning:
            return False, warning
        return True, warning

    def is_windows(self):
        return self.platform_base == "Windows"

    def is_unixlike(self):
        if self.platform_base not in ("Windows", "Windows2016", "Other"):
            return True
        else:
            return False

    def is_support_ansible(self):
        return self.has_protocol('ssh') and self.platform_base not in ("Other",)

    @lazyproperty
    def platform_base(self):
        return self.platform.base

    @property
    def cpu_info(self):
        info = ""
        if self.cpu_model:
            info += self.cpu_model
        if self.cpu_count and self.cpu_cores:
            info += "{}*{}".format(self.cpu_count, self.cpu_cores)
        return info

    @property
    def hardware_info(self):
        if self.cpu_count:
            return '{} Core {} {}'.format(
                self.cpu_vcpus or self.cpu_count * self.cpu_cores,
                self.memory, self.disk_total
            )
        else:
            return ''

    @property
    def connectivity(self):
        if self._connectivity:
            return self._connectivity
        if not self.admin_user:
            return Connectivity.unknown()
        connectivity = self.admin_user.get_asset_connectivity(self)
        return connectivity

    @connectivity.setter
    def connectivity(self, value):
        if not self.admin_user:
            return
        self.admin_user.set_asset_connectivity(self, value)

    def get_auth_info(self):
        if not self.admin_user:
            return {}

        self.admin_user.load_specific_asset_auth(self)
        info = {
            'username': self.admin_user.username,
            'password': self.admin_user.password,
            'private_key': self.admin_user.private_key_file,
        }
        return info

    def as_node(self):
        from .node import Node
        fake_node = Node()
        fake_node.id = self.id
        fake_node.key = self.id
        fake_node.value = self.hostname
        fake_node.asset = self
        fake_node.is_node = False
        return fake_node

    def as_tree_node(self, parent_node):
        from common.tree import TreeNode
        icon_skin = 'file'
        if self.platform_base.lower() == 'windows':
            icon_skin = 'windows'
        elif self.platform_base.lower() == 'linux':
            icon_skin = 'linux'
        data = {
            'id': str(self.id),
            'name': self.hostname,
            'title': self.ip,
            'pId': parent_node.key,
            'isParent': False,
            'open': False,
            'iconSkin': icon_skin,
            'meta': {
                'type': 'asset',
                'asset': {
                    'id': self.id,
                    'hostname': self.hostname,
                    'ip': self.ip,
                    'protocols': self.protocols_as_list,
                    'platform': self.platform_base,
                }
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    class Meta:
        unique_together = [('org_id', 'hostname')]
        verbose_name = _("Asset")

    @classmethod
    def generate_fake(cls, count=100):
        from .user import AdminUser, SystemUser
        from random import seed, choice
        from django.db import IntegrityError
        from .node import Node
        from orgs.utils import get_current_org
        from orgs.models import Organization
        org = get_current_org()
        if not org or not org.is_real():
            Organization.default().change_to()

        nodes = list(Node.objects.all())
        seed()
        for i in range(count):
            ip = [str(i) for i in random.sample(range(255), 4)]
            asset = cls(ip='.'.join(ip),
                        hostname='.'.join(ip),
                        admin_user=choice(AdminUser.objects.all()),
                        created_by='Fake')
            try:
                asset.save()
                asset.protocols = 'ssh/22'
                if nodes and len(nodes) > 3:
                    _nodes = random.sample(nodes, 3)
                else:
                    _nodes = [Node.default_node()]
                asset.nodes.set(_nodes)
                logger.debug('Generate fake asset : %s' % asset.ip)
            except IntegrityError:
                print('Error continue')
                continue
