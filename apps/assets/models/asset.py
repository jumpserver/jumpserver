#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

import uuid
import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from ..const import ASSET_ADMIN_CONN_CACHE_KEY
from .cluster import Cluster
from .group import AssetGroup
from .user import AdminUser, SystemUser

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
        return Node.root()
    except:
        return None


class Asset(models.Model):
    # Important
    PLATFORM_CHOICES = (
        ('Linux', 'Linux'),
        ('Unix', 'Unix'),
        ('MacOS', 'MacOS'),
        ('BSD', 'BSD'),
        ('Windows', 'Windows'),
        ('Other', 'Other'),
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'), db_index=True)
    hostname = models.CharField(max_length=128, unique=True, verbose_name=_('Hostname'))
    port = models.IntegerField(default=22, verbose_name=_('Port'))
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
    memory = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Memory'))
    disk_total = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk total'))
    disk_info = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk info'))

    platform = models.CharField(max_length=128, choices=PLATFORM_CHOICES, default='Linux', verbose_name=_('Platform'))
    os = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('OS'))
    os_version = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('OS version'))
    os_arch = models.CharField(max_length=16, blank=True, null=True, verbose_name=_('OS arch'))
    hostname_raw = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Hostname raw'))

    labels = models.ManyToManyField('assets.Label', blank=True, related_name='assets', verbose_name=_("Labels"))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.hostname

    @property
    def is_valid(self):
        warning = ''
        if not self.is_active:
            warning += ' inactive'
        else:
            return True, ''
        return False, warning

    def is_unixlike(self):
        if self.platform not in ("Windows", "Other"):
            return True
        else:
            return False

    @property
    def hardware_info(self):
        if self.cpu_count:
            return '{} Core {} {}'.format(
                self.cpu_count * self.cpu_cores,
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
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip': self.ip,
            'port': self.port,
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
        unique_together = ('ip', 'port')
        verbose_name = _("Asset")

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            asset = cls(ip='%s.%s.%s.%s' % (i, i, i, i),
                        hostname=forgery_py.internet.user_name(True),
                        admin_user=choice(AdminUser.objects.all()),
                        port=22,
                        created_by='Fake')
            try:
                asset.save()
                asset.system_users = [choice(SystemUser.objects.all()) for i in range(3)]
                asset.groups = [choice(AssetGroup.objects.all()) for i in range(3)]
                logger.debug('Generate fake asset : %s' % asset.ip)
            except IntegrityError:
                print('Error continue')
                continue

