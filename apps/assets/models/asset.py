#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

import uuid
import logging
import random
from functools import reduce
from collections import defaultdict

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from .user import AdminUser, SystemUser
from orgs.mixins import OrgModelMixin, OrgManager

__all__ = ['Asset']
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
        root = Node.root()
        return root
    except:
        return None


class AssetQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def valid(self):
        return self.active()


class Asset(OrgModelMixin):
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

    PROTOCOL_SSH = 'ssh'
    PROTOCOL_RDP = 'rdp'
    PROTOCOL_TELNET = 'telnet'
    PROTOCOL_VNC = 'vnc'
    PROTOCOL_CHOICES = (
        (PROTOCOL_SSH, 'ssh'),
        (PROTOCOL_RDP, 'rdp'),
        (PROTOCOL_TELNET, 'telnet (beta)'),
        (PROTOCOL_VNC, 'vnc'),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    ip = models.CharField(max_length=128, verbose_name=_('IP'), db_index=True)
    hostname = models.CharField(max_length=128, verbose_name=_('Hostname'))
    protocol = models.CharField(max_length=128, default=PROTOCOL_SSH, choices=PROTOCOL_CHOICES, verbose_name=_('Protocol'))
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    platform = models.CharField(max_length=128, choices=PLATFORM_CHOICES, default='Linux', verbose_name=_('Platform'))
    domain = models.ForeignKey("assets.Domain", null=True, blank=True, related_name='assets', verbose_name=_("Domain"), on_delete=models.SET_NULL)
    nodes = models.ManyToManyField('assets.Node', default=default_node, related_name='assets', verbose_name=_("Nodes"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    # Auth
    admin_user = models.ForeignKey('assets.AdminUser', on_delete=models.PROTECT, null=True, verbose_name=_("Admin user"))

    # Some information
    public_ip = models.GenericIPAddressField(max_length=32, blank=True, null=True, verbose_name=_('Public IP'))
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

    objects = OrgManager.from_queryset(AssetQuerySet)()
    CONNECTIVITY_CACHE_KEY = '_JMS_ASSET_CONNECTIVITY_{}'
    UNREACHABLE, REACHABLE, UNKNOWN = range(0, 3)
    CONNECTIVITY_CHOICES = (
        (UNREACHABLE, _("Unreachable")),
        (REACHABLE, _('Reachable')),
        (UNKNOWN, _("Unknown")),
    )

    def __str__(self):
        return '{0.hostname}({0.ip})'.format(self)

    @property
    def is_valid(self):
        warning = ''
        if not self.is_active:
            warning += ' inactive'
        else:
            return True, ''
        return False, warning

    def support_ansible(self):
        if self.platform in ("Windows", "Windows2016", "Other"):
            return False
        if self.protocol != 'ssh':
            return False
        return True

    def is_unixlike(self):
        if self.platform not in ("Windows", "Windows2016"):
            return True
        else:
            return False

    def get_nodes(self):
        from .node import Node
        nodes = self.nodes.all() or [Node.root()]
        return nodes

    def get_all_nodes(self, flat=False):
        nodes = []
        for node in self.get_nodes():
            _nodes = node.get_ancestor(with_self=True)
            nodes.append(_nodes)
        if flat:
            nodes = list(reduce(lambda x, y: set(x) | set(y), nodes))
        return nodes

    @classmethod
    def get_queryset_by_fullname_list(cls, fullname_list):
        org_fullname_map = defaultdict(list)
        for fullname in fullname_list:
            hostname, org = cls.split_fullname(fullname)
            org_fullname_map[org].append(hostname)
        filter_arg = Q()
        for org, hosts in org_fullname_map.items():
            if org.is_real():
                filter_arg |= Q(hostname__in=hosts, org_id=org.id)
            else:
                filter_arg |= Q(Q(org_id__isnull=True) | Q(org_id=''), hostname__in=hosts)
        return Asset.objects.filter(filter_arg)

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
        if not self.is_unixlike():
            return self.REACHABLE
        key = self.CONNECTIVITY_CACHE_KEY.format(str(self.id))
        cached = cache.get(key, None)
        return cached if cached is not None else self.UNKNOWN

    @connectivity.setter
    def connectivity(self, value):
        key = self.CONNECTIVITY_CACHE_KEY.format(str(self.id))
        cache.set(key, value, 3600*2)

    def get_auth_info(self):
        if self.admin_user:
            self.admin_user.load_specific_asset_auth(self)
            return {
                'username': self.admin_user.username,
                'password': self.admin_user.password,
                'private_key': self.admin_user.private_key_file,
                'become': self.admin_user.become_info,
            }

    def as_node(self):
        from .node import Node
        fake_node = Node()
        fake_node.id = self.id
        fake_node.key = self.id
        fake_node.value = self.hostname
        fake_node.asset = self
        fake_node.is_node = False
        return fake_node

    def to_json(self):
        info = {
            'id': self.id,
            'hostname': self.hostname,
            'ip': self.ip,
            'port': self.port,
        }
        if self.domain and self.domain.gateway_set.all():
            info["gateways"] = [d.id for d in self.domain.gateway_set.all()]
        return info

    def _to_secret_json(self):
        """
        Ansible use it create inventory
        Todo: May be move to ops implements it
        """
        data = self.to_json()
        if self.admin_user:
            self.admin_user.load_specific_asset_auth(self)
            admin_user = self.admin_user
            data.update({
                'username': admin_user.username,
                'password': admin_user.password,
                'private_key': admin_user.private_key_file,
                'become': admin_user.become_info,
                'groups': [node.value for node in self.nodes.all()],
            })
        return data

    def as_tree_node(self, parent_node):
        from common.tree import TreeNode
        icon_skin = 'file'
        if self.platform.lower() == 'windows':
            icon_skin = 'windows'
        elif self.platform.lower() == 'linux':
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
                    'port': self.port,
                    'platform': self.platform,
                    'protocol': self.protocol,
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
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError
        from .node import Node
        nodes = list(Node.objects.all())
        seed()
        for i in range(count):
            ip = [str(i) for i in random.sample(range(255), 4)]
            asset = cls(ip='.'.join(ip),
                        hostname=forgery_py.internet.user_name(True),
                        admin_user=choice(AdminUser.objects.all()),
                        port=22,
                        created_by='Fake')
            try:
                asset.save()
                if nodes and len(nodes) > 3:
                    _nodes = random.sample(nodes, 3)
                else:
                    _nodes = [Node.default_node()]
                asset.nodes.set(_nodes)
                asset.system_users = [choice(SystemUser.objects.all()) for i in range(3)]
                logger.debug('Generate fake asset : %s' % asset.ip)
            except IntegrityError:
                print('Error continue')
                continue
