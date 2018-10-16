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

from ..const import ASSET_ADMIN_CONN_CACHE_KEY
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

    SSH_PROTOCOL = 'ssh'
    RDP_PROTOCOL = 'rdp'
    TELNET_PROTOCOL = 'telnet'
    PROTOCOL_CHOICES = (
        (SSH_PROTOCOL, 'ssh'),
        (RDP_PROTOCOL, 'rdp'),
        (TELNET_PROTOCOL, 'telnet (beta)'),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'), db_index=True)
    hostname = models.CharField(max_length=128, verbose_name=_('Hostname'))
    protocol = models.CharField(max_length=128, default=SSH_PROTOCOL, choices=PROTOCOL_CHOICES, verbose_name=_('Protocol'))
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    platform = models.CharField(max_length=128, choices=PLATFORM_CHOICES, default='Linux', verbose_name=_('Platform'))
    domain = models.ForeignKey("assets.Domain", null=True, blank=True,
                               related_name='assets', verbose_name=_("Domain"),
                               on_delete=models.SET_NULL)
    nodes = models.ManyToManyField('assets.Node', default=default_node,
                                   related_name='assets',
                                   verbose_name=_("Nodes"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    # Auth
    admin_user = models.ForeignKey('assets.AdminUser', on_delete=models.PROTECT,
                                   null=True, verbose_name=_("Admin user"))

    # Some information
    public_ip = models.GenericIPAddressField(max_length=32, blank=True, null=True, verbose_name=_('Public IP'))
    number = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Asset number'))

    # Collect
    vendor = models.CharField(max_length=64, null=True, blank=True,
                              verbose_name=_('Vendor'))
    model = models.CharField(max_length=54, null=True, blank=True,
                             verbose_name=_('Model'))
    sn = models.CharField(max_length=128, null=True, blank=True,
                          verbose_name=_('Serial number'))

    cpu_model = models.CharField(max_length=64, null=True, blank=True,
                                 verbose_name=_('CPU model'))
    cpu_count = models.IntegerField(null=True, verbose_name=_('CPU count'))
    cpu_cores = models.IntegerField(null=True, verbose_name=_('CPU cores'))
    cpu_vcpus = models.IntegerField(null=True, verbose_name=_('CPU vcpus'))
    memory = models.CharField(max_length=64, null=True, blank=True,
                              verbose_name=_('Memory'))
    disk_total = models.CharField(max_length=1024, null=True, blank=True,
                                  verbose_name=_('Disk total'))
    disk_info = models.CharField(max_length=1024, null=True, blank=True,
                                 verbose_name=_('Disk info'))

    os = models.CharField(max_length=128, null=True, blank=True,
                          verbose_name=_('OS'))
    os_version = models.CharField(max_length=16, null=True, blank=True,
                                  verbose_name=_('OS version'))
    os_arch = models.CharField(max_length=16, blank=True, null=True,
                               verbose_name=_('OS arch'))
    hostname_raw = models.CharField(max_length=128, blank=True, null=True,
                                    verbose_name=_('Hostname raw'))

    labels = models.ManyToManyField('assets.Label', blank=True,
                                    related_name='assets',
                                    verbose_name=_("Labels"))
    created_by = models.CharField(max_length=32, null=True, blank=True,
                                  verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True,
                                        blank=True,
                                        verbose_name=_('Date created'))
    comment = models.TextField(max_length=128, default='', blank=True,
                               verbose_name=_('Comment'))

    objects = OrgManager.from_queryset(AssetQuerySet)()

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
            _nodes.append(_nodes)
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
    def is_connective(self):
        if not self.is_unixlike():
            return True
        val = cache.get(ASSET_ADMIN_CONN_CACHE_KEY.format(self.hostname))
        if val == 1:
            return True
        else:
            return False

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

    def get_auth_info(self):
        if self.admin_user:
            return {
                'username': self.admin_user.username,
                'password': self.admin_user.password,
                'private_key': self.admin_user.private_key_file,
                'become': self.admin_user.become_info,
            }

    def _to_secret_json(self):
        """
        Ansible use it create inventory, First using asset user,
        otherwise using cluster admin user

        Todo: May be move to ops implements it
        """
        data = self.to_json()
        if self.admin_user:
            admin_user = self.admin_user
            data.update({
                'username': admin_user.username,
                'password': admin_user.password,
                'private_key': admin_user.private_key_file,
                'become': admin_user.become_info,
                'groups': [node.value for node in self.nodes.all()],
            })
        return data

    class Meta:
        unique_together = [('org_id', 'hostname')]
        verbose_name = _("Asset")

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError

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
                asset.system_users = [choice(SystemUser.objects.all()) for i in range(3)]
                logger.debug('Generate fake asset : %s' % asset.ip)
            except IntegrityError:
                print('Error continue')
                continue
