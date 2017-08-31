#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
import os
import logging
from hashlib import md5

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils import signer, validate_ssh_private_key, ssh_key_string_to_obj

__all__ = ['AdminUser', 'SystemUser', 'private_key_validator']
logger = logging.getLogger(__name__)


def private_key_validator(value):
    if not validate_ssh_private_key(value):
        raise ValidationError(
            _('%(value)s is not an even number'),
            params={'value': value},
        )


class AdminUser(models.Model):
    BECOME_METHOD_CHOICES = (
        ('sudo', 'sudo'),
        ('su', 'su'),
    )
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    _password = models.CharField(
        max_length=256, blank=True, null=True, verbose_name=_('Password'))
    _private_key = models.TextField(max_length=4096, blank=True, null=True, verbose_name=_('SSH private key'),
                                    validators=[private_key_validator,])
    become = models.BooleanField(default=True)
    become_method = models.CharField(choices=BECOME_METHOD_CHOICES, default='sudo', max_length=4)
    become_user = models.CharField(default='root', max_length=64)
    become_pass = models.CharField(default='', max_length=128)
    _public_key = models.TextField(
        max_length=4096, blank=True, verbose_name=_('SSH public key'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.CharField(
        max_length=32, null=True, verbose_name=_('Created by'))

    def __unicode__(self):
        return self.name
    __str__ = __unicode__

    @property
    def password(self):
        if self._password:
            return signer.unsign(self._password)
        else:
            return ''

    @password.setter
    def password(self, password_raw):
        self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        if self._private_key:
            key_str = signer.unsign(self._private_key)
            return ssh_key_string_to_obj(key_str)
        else:
            return None

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = signer.sign(private_key_raw)

    @property
    def private_key_file(self):
        if not self.private_key:
            return None
        project_dir = settings.PROJECT_DIR
        tmp_dir = os.path.join(project_dir, 'tmp')
        key_name = md5(self._private_key.encode()).hexdigest()
        key_path = os.path.join(tmp_dir, key_name)
        if not os.path.exists(key_path):
            self.private_key.write_private_key_file(key_path)
        return key_path

    @property
    def public_key(self):
        return signer.unsign(self._public_key)

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = signer.sign(public_key_raw)

    @property
    def assets_amount(self):
        return self.assets.count()

    class Meta:
        ordering = ['name']

    @classmethod
    def generate_fake(cls, count=10):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue


class SystemUser(models.Model):
    PROTOCOL_CHOICES = (
        ('ssh', 'ssh'),
    )
    AUTH_METHOD_CHOICES = (
        ('P', 'Password'),
        ('K', 'Public key'),
    )
    name = models.CharField(max_length=128, unique=True,
                            verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    _password = models.CharField(
        max_length=256, blank=True, verbose_name=_('Password'))
    protocol = models.CharField(
        max_length=16, choices=PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    _private_key = models.TextField(
        max_length=8192, blank=True, verbose_name=_('SSH private key'))
    _public_key = models.TextField(
        max_length=8192, blank=True, verbose_name=_('SSH public key'))
    auth_method = models.CharField(choices=AUTH_METHOD_CHOICES, default='K',
                                   max_length=1, verbose_name=_('Auth method'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(
        max_length=4096, default='/sbin/ifconfig', verbose_name=_('Sudo'))
    shell = models.CharField(
        max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(
        max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(
        max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name
    __str__ = __unicode__

    @property
    def password(self):
        if self._password:
            return signer.unsign(self._password)
        return None

    @password.setter
    def password(self, password_raw):
        self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        if self._private_key:
            return signer.unsign(self._private_key)
        return None

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = signer.sign(private_key_raw)

    @property
    def public_key(self):
        return signer.unsign(self._public_key)

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = signer.sign(public_key_raw)

    def get_assets_inherit_from_asset_groups(self):
        assets = set()
        asset_groups = self.asset_groups.all()
        for asset_group in asset_groups:
            for asset in asset_group.assets.all():
                setattr(asset, 'is_inherit_from_asset_groups', True)
                setattr(asset, 'inherit_from_asset_groups',
                        getattr(asset, 'inherit_from_asset_groups', set()).add(asset_group))
                assets.add(asset)
        return assets

    def get_assets(self):
        assets = set(self.assets.all()
                     ) | self.get_assets_inherit_from_asset_groups()
        return list(assets)

    def _to_secret_json(self):
        """Push system user use it"""
        return {
            'name': self.name,
            'username': self.username,
            'shell': self.shell,
            'sudo': self.sudo,
            'password': self.password,
            'public_key': self.public_key
        }

    @property
    def assets_amount(self):
        return self.assets.count()

    @property
    def asset_group_amount(self):
        return self.asset_groups.count()

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'protocol': self.protocol,
            'auth_method': self.auth_method,
            'auto_push': self.auto_push,
        }

    class Meta:
        ordering = ['name']

    @classmethod
    def generate_fake(cls, count=10):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue



