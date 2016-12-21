#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from __future__ import unicode_literals

from django.db import models
import logging
from django.utils.translation import ugettext_lazy as _

from . import IDC, AssetGroup, AdminUser, SystemUser

__all__ = ['Asset', 'Tag']
logger = logging.getLogger(__name__)


def get_default_idc():
    return IDC.initial()


class Asset(models.Model):
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

    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'), db_index=True)
    other_ip = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Other IP'))
    remote_card_ip = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('Remote card IP'))
    hostname = models.CharField(max_length=128, unique=True, verbose_name=_('Hostname'))
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    groups = models.ManyToManyField(AssetGroup, blank=True, related_name='assets', verbose_name=_('Asset groups'))
    admin_user = models.ForeignKey(AdminUser, null=True, blank=True, related_name='assets',
                                   on_delete=models.SET_NULL, verbose_name=_("Admin user"))
    system_users = models.ManyToManyField(SystemUser, blank=True, related_name='assets', verbose_name=_("System User"))
    idc = models.ForeignKey(IDC, blank=True, null=True, related_name='assets',
                            on_delete=models.SET_NULL, verbose_name=_('IDC'),)
    mac_address = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("Mac address"))
    brand = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Brand'))
    cpu = models.CharField(max_length=64,  null=True, blank=True, verbose_name=_('CPU'))
    memory = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Memory'))
    disk = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk'))
    os = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('OS'))
    cabinet_no = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Cabinet number'))
    cabinet_pos = models.IntegerField(null=True, blank=True, verbose_name=_('Cabinet position'))
    number = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Asset number'))
    status = models.CharField(choices=STATUS_CHOICES, max_length=8, null=True, blank=True,
                              default='In use', verbose_name=_('Asset status'))
    type = models.CharField(choices=TYPE_CHOICES, max_length=16, blank=True, null=True,
                            default='Server', verbose_name=_('Asset type'),)
    env = models.CharField(choices=ENV_CHOICES, max_length=8, blank=True, null=True,
                           default='Prod', verbose_name=_('Asset environment'),)
    sn = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Serial number'))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date added'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))
    tags = models.ManyToManyField('Tag', blank=True, verbose_name=_('Tags'))

    def __unicode__(self):
        return '%(ip)s:%(port)s' % {'ip': self.ip, 'port': self.port}

    __str__ = __unicode__

    @property
    def is_valid(self):
        warning = ''
        if not self.is_active:
            warning += ' inactive'
        else:
            return True, ''
        return False, warning

    def to_json(self):
        pass

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
                        idc=choice(IDC.objects.all()),
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


class Tag(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    created_time = models.DateTimeField(auto_now_add=True, verbose_name=_('Create time'))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))

    def __unicode__(self):
        return self.name

    __str__ = __unicode__

    class Meta:
        ordering = ['name']
