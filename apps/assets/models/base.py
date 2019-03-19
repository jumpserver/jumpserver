# -*- coding: utf-8 -*-
#
import os
import uuid
from hashlib import md5

import sshpubkeys
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils import (
    get_signer, ssh_key_string_to_obj, ssh_key_gen, get_logger
)
from common.validators import alphanumeric
from orgs.mixins import OrgModelMixin
from .utils import private_key_validator

signer = get_signer()

logger = get_logger(__file__)


class AssetUser(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    username = models.CharField(max_length=32, blank=True, verbose_name=_('Username'), validators=[alphanumeric])
    _password = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    _private_key = models.TextField(max_length=4096, blank=True, null=True, verbose_name=_('SSH private key'), validators=[private_key_validator, ])
    _public_key = models.TextField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    UNREACHABLE, REACHABLE, UNKNOWN = range(0, 3)
    CONNECTIVITY_CHOICES = (
        (UNREACHABLE, _("Unreachable")),
        (REACHABLE, _('Reachable')),
        (UNKNOWN, _("Unknown")),
    )

    @property
    def password(self):
        if self._password:
            return signer.unsign(self._password)
        else:
            return None

    @password.setter
    def password(self, password_raw):
        # raise AttributeError("Using set_auth do that")
        self._password = signer.sign(password_raw)

    @property
    def private_key(self):
        if self._private_key:
            return signer.unsign(self._private_key)

    @private_key.setter
    def private_key(self, private_key_raw):
        # raise AttributeError("Using set_auth do that")
        self._private_key = signer.sign(private_key_raw)

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

    @public_key.setter
    def public_key(self, public_key_raw):
        # raise AttributeError("Using set_auth do that")
        self._public_key = signer.sign(public_key_raw)

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

    def get_auth(self, asset=None):
        pass

    def load_specific_asset_auth(self, asset):
        from ..backends.multi import AssetUserManager
        try:
            other = AssetUserManager.get(username=self.username, asset=asset)
        except Exception as e:
            logger.error(e, exc_info=True)
        else:
            self._merge_auth(other)

    def _merge_auth(self, other):
        if not other:
            return
        if other.password:
            self.password = other.password
        if other.public_key:
            self.public_key = other.public_key
        if other.private_key:
            self.private_key = other.private_key

    def clear_auth(self):
        self._password = ''
        self._private_key = ''
        self._public_key = ''
        self.save()

    def auto_gen_auth(self):
        password = str(uuid.uuid4())
        private_key, public_key = ssh_key_gen(
            username=self.username
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
