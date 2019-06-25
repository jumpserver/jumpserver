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
from common import fields
from orgs.mixins import OrgModelMixin
from .utils import private_key_validator, Connectivity

signer = get_signer()

logger = get_logger(__file__)


class AssetUser(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    username = models.CharField(max_length=32, blank=True, verbose_name=_('Username'), validators=[alphanumeric])
    password = fields.EncryptCharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    private_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH private key'), validators=[private_key_validator, ])
    public_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH public key'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    CONNECTIVITY_ASSET_CACHE_KEY = "ASSET_USER_ASSET_CONNECTIVITY_{}"

    _prefer = "system_user"

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
    def public_key_obj(self):
        if self.public_key:
            try:
                return sshpubkeys.SSHKey(self.public_key)
            except TabError:
                pass
        return None

    def get_related_assets(self):
        assets = self.assets.all()
        return assets

    def set_auth(self, password=None, private_key=None, public_key=None):
        update_fields = []
        if password:
            self.password = password
            update_fields.append('password')
        if private_key:
            self.private_key = private_key
            update_fields.append('private_key')
        if public_key:
            self.public_key = public_key
            update_fields.append('public_key')

        if update_fields:
            self.save(update_fields=update_fields)

    def set_connectivity(self, summary):
        unreachable = summary.get('dark', {}).keys()
        reachable = summary.get('contacted', {}).keys()

        for asset in self.get_related_assets():
            if asset.hostname in unreachable:
                self.set_asset_connectivity(asset, Connectivity.unreachable())
            elif asset.hostname in reachable:
                self.set_asset_connectivity(asset, Connectivity.reachable())
            else:
                self.set_asset_connectivity(asset, Connectivity.unknown())

    @property
    def connectivity(self):
        assets = self.get_related_assets()
        data = {
            'unreachable': [],
            'reachable': [],
            'unknown': [],
        }
        for asset in assets:
            connectivity = self.get_asset_connectivity(asset)
            if connectivity.is_reachable():
                data["reachable"].append(asset.hostname)
            elif connectivity.is_unreachable():
                data["unreachable"].append(asset.hostname)
            else:
                data["unknown"].append(asset.hostname)
        return data

    @property
    def connectivity_amount(self):
        return {k: len(v) for k, v in self.connectivity.items()}

    @property
    def assets_amount(self):
        return self.get_related_assets().count()

    def get_asset_connectivity(self, asset):
        i = self.generate_id_with_asset(asset)
        key = self.CONNECTIVITY_ASSET_CACHE_KEY.format(i)
        return Connectivity.get(key)

    def set_asset_connectivity(self, asset, c):
        i = self.generate_id_with_asset(asset)
        key = self.CONNECTIVITY_ASSET_CACHE_KEY.format(i)
        Connectivity.set(key, c)

    def get_asset_user(self, asset):
        from ..backends import AssetUserManager
        try:
            manager = AssetUserManager().prefer(self._prefer)
            other = manager.get(username=self.username, asset=asset)
            return other
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def load_specific_asset_auth(self, asset):
        instance = self.get_asset_user(asset)
        if instance:
            self._merge_auth(instance)

    def _merge_auth(self, other):
        self.password = other.password
        self.public_key = other.public_key
        self.private_key = other.private_key

    def clear_auth(self):
        self.password = ''
        self.private_key = ''
        self.public_key = ''
        self.save()

    def auto_gen_auth(self):
        password = str(uuid.uuid4())
        private_key, public_key = ssh_key_gen(
            username=self.username
        )
        self.set_auth(
            password=password, private_key=private_key,
            public_key=public_key
        )

    def auto_gen_auth_password(self):
        password = str(uuid.uuid4())
        self.set_auth(password=password)

    def _to_secret_json(self):
        """Push system user use it"""
        return {
            'name': self.name,
            'username': self.username,
            'password': self.password,
            'public_key': self.public_key,
            'private_key': self.private_key_file,
        }

    def generate_id_with_asset(self, asset):
        user_id = str(self.id).split('-')[:3]
        asset_id = str(asset.id).split('-')[3:]
        ids = user_id + asset_id
        return '-'.join(ids)

    def construct_to_authbook(self, asset):
        from . import AuthBook
        fields = [
            'name', 'username', 'comment', 'org_id',
            'password', 'private_key', 'public_key',
            'date_created', 'date_updated', 'created_by'
        ]
        i = self.generate_id_with_asset(asset)
        obj = AuthBook(id=i, asset=asset, version=0, is_latest=True)
        for field in fields:
            value = getattr(self, field)
            setattr(obj, field, value)
        return obj

    class Meta:
        abstract = True

