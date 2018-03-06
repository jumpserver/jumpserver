#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import os
import logging
import uuid
from hashlib import md5

import sshpubkeys
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils import get_signer, ssh_key_string_to_obj, ssh_key_gen
from .utils import private_key_validator
from ..const import SYSTEM_USER_CONN_CACHE_KEY


__all__ = ['AdminUser', 'SystemUser',]
logger = logging.getLogger(__name__)
signer = get_signer()


class AssetUser(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=128, verbose_name=_('Username'))
    _password = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    _private_key = models.TextField(max_length=4096, blank=True, null=True, verbose_name=_('SSH private key'), validators=[private_key_validator, ])
    _public_key = models.TextField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    @property
    def password(self):
        if self._password:
            return signer.unsign(self._password)
        else:
            return None

    @password.setter
    def password(self, password_raw):
        raise AttributeError("Using set_auth do that")
        # self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        if self._private_key:
            return signer.unsign(self._private_key)

    @private_key.setter
    def private_key(self, private_key_raw):
        raise AttributeError("Using set_auth do that")
        # self._private_key = signer.sign(private_key_raw)

    @property
    def private_key_obj(self):
        if self._private_key:
            key_str = signer.unsign(self._private_key)
            return ssh_key_string_to_obj(key_str, password=self.password)
        else:
            return None

    @property
    def private_key_file(self):
        if not self.private_key_obj:
            return None
        project_dir = settings.PROJECT_DIR
        tmp_dir = os.path.join(project_dir, 'tmp')
        key_str = signer.unsign(self._private_key)
        key_name = '.' + md5(key_str.encode('utf-8')).hexdigest()
        key_path = os.path.join(tmp_dir, key_name)
        if not os.path.exists(key_path):
            self.private_key_obj.write_private_key_file(key_path)
            os.chmod(key_path, 0o400)
        return key_path

    @property
    def public_key(self):
        key = signer.unsign(self._public_key)
        if key:
            return key
        else:
            return None

    @property
    def public_key_obj(self):
        if self.public_key:
            try:
                return sshpubkeys.SSHKey(self.public_key)
            except TabError:
                pass
        return None

    def set_auth(self, password=None, private_key=None, public_key=None):
        update_fields = []
        if password:
            self._password = signer.sign(password)
            update_fields.append('_password')
        if private_key:
            self._private_key = signer.sign(private_key)
            update_fields.append('_private_key')
        if public_key:
            self._public_key = signer.sign(public_key)
            update_fields.append('_public_key')

        if update_fields:
            self.save(update_fields=update_fields)

    def auto_gen_auth(self):
        password = str(uuid.uuid4())
        private_key, public_key = ssh_key_gen(
            username=self.name, password=password
        )
        self.set_auth(password=password,
                      private_key=private_key,
                      public_key=public_key)

    def _to_secret_json(self):
        """Push system user use it"""
        return {
            'name': self.name,
            'username': self.username,
            'password': self.password,
            'public_key': self.public_key,
            'private_key': self.private_key_file,
        }

    class Meta:
        abstract = True


class AdminUser(AssetUser):
    """
    A privileged user that ansible can use it to push system user and so on
    """
    BECOME_METHOD_CHOICES = (
        ('sudo', 'sudo'),
        ('su', 'su'),
    )
    become = models.BooleanField(default=True)
    become_method = models.CharField(choices=BECOME_METHOD_CHOICES, default='sudo', max_length=4)
    become_user = models.CharField(default='root', max_length=64)
    _become_pass = models.CharField(default='', max_length=128)

    def __str__(self):
        return self.name

    @property
    def become_pass(self):
        password = signer.unsign(self._become_pass)
        if password:
            return password
        else:
            return ""

    @become_pass.setter
    def become_pass(self, password):
        self._become_pass = signer.sign(password)

    @property
    def become_info(self):
        if self.become:
            info = {
                "method": self.become_method,
                "user": self.become_user,
                "pass": self.become_pass,
            }
        else:
            info = None
        return info

    def get_related_assets(self):
        assets = self.asset_set.all()
        return assets

    @property
    def assets_amount(self):
        return self.get_related_assets().count()

    class Meta:
        ordering = ['name']
        verbose_name = _("Admin user")

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


class SystemUser(AssetUser):
    SSH_PROTOCOL = 'ssh'
    RDP_PROTOCOL = 'rdp'
    PROTOCOL_CHOICES = (
        (SSH_PROTOCOL, 'ssh'),
        (RDP_PROTOCOL, 'rdp'),
    )

    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Nodes"))
    priority = models.IntegerField(default=10, verbose_name=_("Priority"))
    protocol = models.CharField(max_length=16, choices=PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(default='/sbin/ifconfig', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))

    def __str__(self):
        return self.name

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'protocol': self.protocol,
            'priority': self.priority,
            'auto_push': self.auto_push,
        }

    @property
    def assets(self):
        assets = set()
        for node in self.nodes.all():
            assets.update(set(node.get_all_assets()))
        return assets

    @property
    def assets_connective(self):
        _result = cache.get(SYSTEM_USER_CONN_CACHE_KEY.format(self.name), {})
        return _result

    @property
    def unreachable_assets(self):
        return list(self.assets_connective.get('dark', {}).keys())

    @property
    def reachable_assets(self):
        return self.assets_connective.get('contacted', [])

    def is_need_push(self):
        if self.auto_push and self.protocol == self.__class__.SSH_PROTOCOL:
            return True
        else:
            return False

    class Meta:
        ordering = ['name']
        verbose_name = _("System user")

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



