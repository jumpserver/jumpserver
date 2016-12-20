#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.db import models
import logging
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from common.utils import signer, validate_ssh_private_key

__all__ = ['AdminUser', 'SystemUser', 'private_key_validator']
logger = logging.getLogger(__name__)


def private_key_validator(value):
    if not validate_ssh_private_key(value):
        raise ValidationError(
            _('%(value)s is not an even number'),
            params={'value': value},
        )


class AdminUser(models.Model):
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    _password = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    _private_key = models.CharField(max_length=4096, blank=True, null=True, verbose_name=_('SSH private key'),
                                    validators=[private_key_validator,])
    _public_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    created_by = models.CharField(max_length=32, null=True, verbose_name=_('Created by'))

    def __unicode__(self):
        return self.name

    @property
    def password(self):
        return signer.unsign(self._password)

    @password.setter
    def password(self, password_raw):
        self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        return signer.unsign(self._private_key)

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = signer.sign(private_key_raw)

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
        db_table = 'admin_user'

    @classmethod
    def generate_fake(cls, count=100):
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
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, verbose_name=_('Username'))
    _password = models.CharField(max_length=256, blank=True, verbose_name=_('Password'))
    protocol = models.CharField(max_length=16, choices=PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    _private_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH private key'))
    _public_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    as_default = models.BooleanField(default=False, verbose_name=_('As default'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    auto_update = models.BooleanField(default=True, verbose_name=_('Auto update pass/key'))
    sudo = models.TextField(max_length=4096, default='/user/bin/whoami', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    home = models.CharField(max_length=64, blank=True, verbose_name=_('Home'))
    uid = models.IntegerField(null=True, blank=True, verbose_name=_('Uid'))
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    @property
    def password(self):
        return signer.unsign(self._password)

    @password.setter
    def password(self, password_raw):
        self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        return signer.unsign(self._private_key)

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
                        getattr(asset, b'inherit_from_asset_groups', set()).add(asset_group))
                assets.add(asset)
        return assets

    def get_assets(self):
        assets = set(self.assets.all()) | self.get_assets_inherit_from_asset_groups()
        return list(assets)

    @property
    def assets_amount(self):
        return self.assets.count()

    @property
    def asset_group_amount(self):
        return self.asset_groups.count()

    class Meta:
        db_table = 'system_user'

    @classmethod
    def generate_fake(cls, count=100):
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

