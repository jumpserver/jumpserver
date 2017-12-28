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


class Asset(models.Model):
    # Todo: Move them to settings
    STATUS_CHOICES = (
        ('In use', _('In use')),
        ('Out of use', _('Out of use')),
    )
    TYPE_CHOICES = (
        ('Server', _('Server')),
        ('VM', _('VM')),
        ('Switch', _('Switch')),
        ('Router', _('Router')),
        ('Firewall', _('Firewall')),
        ('Storage', _("Storage")),
    )
    ENV_CHOICES = (
        ('Prod', 'Production'),
        ('Dev', 'Development'),
        ('Test', 'Testing'),
    )

    # Important
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'), db_index=True)
    hostname = models.CharField(max_length=128, unique=True, verbose_name=_('Hostname'))
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    groups = models.ManyToManyField(AssetGroup, blank=True, related_name='assets', verbose_name=_('Asset groups'))
    cluster = models.ForeignKey(Cluster, blank=True, null=True, related_name='assets', on_delete=models.SET_NULL, verbose_name=_('Cluster'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    type = models.CharField(choices=TYPE_CHOICES, max_length=16, blank=True, null=True, default='Server', verbose_name=_('Asset type'),)
    env = models.CharField(choices=ENV_CHOICES, max_length=8, blank=True, null=True, default='Prod', verbose_name=_('Asset environment'),)
    status = models.CharField(choices=STATUS_CHOICES, max_length=12, null=True, blank=True, default='In use', verbose_name=_('Asset status'))

    # Auth
    admin_user = models.ForeignKey('assets.AdminUser', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Admin user"))

    # Some information
    public_ip = models.GenericIPAddressField(max_length=32, blank=True, null=True, verbose_name=_('Public IP'))
    remote_card_ip = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('Remote control card IP'))
    cabinet_no = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Cabinet number'))
    cabinet_pos = models.IntegerField(null=True, blank=True, verbose_name=_('Cabinet position'))
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

    platform = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Platform'))
    os = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('OS'))
    os_version = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('OS version'))
    os_arch = models.CharField(max_length=16, blank=True, null=True, verbose_name=_('OS arch'))
    hostname_raw = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Hostname raw'))

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
        val = cache.get(ASSET_ADMIN_CONN_CACHE_KEY.format(self.hostname))
        if val == 1:
            return True
        else:
            return False

    @property
    def admin_user_avail(self):
        if self.admin_user:
            admin_user = self.admin_user
        elif self.cluster and self.cluster.admin_user:
            admin_user = self.cluster.admin_user
        else:
            return None
        return admin_user

    @property
    def is_has_private_admin_user(self):
        if self.admin_user:
            return True
        else:
            return False

    def to_json(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip': self.ip,
            'port': self.port,
            'groups': [group.name for group in self.groups.all()],
        }

    def _to_secret_json(self):
        """
        Ansible use it create inventory, First using asset user,
        otherwise using cluster admin user

        Todo: May be move to ops implements it
        """
        data = self.to_json()
        if self.admin_user_avail:
            admin_user = self.admin_user_avail
            data.update({
                'username': admin_user.username,
                'password': admin_user.password,
                'private_key': admin_user.private_key_file,
                'become': admin_user.become_info,
            })
        return data

    class Meta:
        unique_together = ('ip', 'port')

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
                        cluster=choice(Cluster.objects.all()),
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

