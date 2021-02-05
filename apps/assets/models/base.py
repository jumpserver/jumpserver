# -*- coding: utf-8 -*-
#
import io
import os
import uuid
from hashlib import md5

import sshpubkeys
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.utils.common import timeit
from common.utils import (
    ssh_key_string_to_obj, ssh_key_gen, get_logger, lazyproperty
)
from common.validators import alphanumeric
from common import fields
from orgs.mixins.models import OrgModelMixin
from .utils import Connectivity


logger = get_logger(__file__)


class ConnectivityMixin:
    CONNECTIVITY_ASSET_CACHE_KEY = "ASSET_USER_{}_{}_ASSET_CONNECTIVITY"
    CONNECTIVITY_AMOUNT_CACHE_KEY = "ASSET_USER_{}_{}_CONNECTIVITY_AMOUNT"
    ASSET_USER_CACHE_TIME = 3600 * 24
    id = ''
    username = ''

    @property
    def part_id(self):
        i = '-'.join(str(self.id).split('-')[:3])
        return i

    def set_connectivity(self, summary):
        unreachable = summary.get('dark', {}).keys()
        reachable = summary.get('contacted', {}).keys()

        assets = self.get_related_assets()
        if not isinstance(assets, list):
            assets = assets.only('id', 'hostname', 'admin_user__id')
        for asset in assets:
            if asset.hostname in unreachable:
                self.set_asset_connectivity(asset, Connectivity.unreachable())
            elif asset.hostname in reachable:
                self.set_asset_connectivity(asset, Connectivity.reachable())
            else:
                self.set_asset_connectivity(asset, Connectivity.unknown())
        cache_key = self.CONNECTIVITY_AMOUNT_CACHE_KEY.format(self.username, self.part_id)
        cache.delete(cache_key)

    @property
    def connectivity(self):
        assets = self.get_related_assets()
        if not isinstance(assets, list):
            assets = assets.only('id', 'hostname', 'admin_user__id')
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
        cache_key = self.CONNECTIVITY_AMOUNT_CACHE_KEY.format(self.username, self.part_id)
        amount = cache.get(cache_key)
        if not amount:
            amount = {k: len(v) for k, v in self.connectivity.items()}
            cache.set(cache_key, amount, self.ASSET_USER_CACHE_TIME)
        return amount

    @classmethod
    def get_asset_username_connectivity(cls, asset, username):
        key = cls.CONNECTIVITY_ASSET_CACHE_KEY.format(username, asset.id)
        return Connectivity.get(key)

    def get_asset_connectivity(self, asset):
        key = self.get_asset_connectivity_key(asset)
        return Connectivity.get(key)

    def get_asset_connectivity_key(self, asset):
        return self.CONNECTIVITY_ASSET_CACHE_KEY.format(self.username, asset.id)

    def set_asset_connectivity(self, asset, c):
        key = self.get_asset_connectivity_key(asset)
        Connectivity.set(key, c)


class AuthMixin:
    private_key = ''
    password = ''
    public_key = ''
    username = ''
    _prefer = 'system_user'

    @property
    def private_key_obj(self):
        if self.private_key:
            key_obj = ssh_key_string_to_obj(self.private_key, password=self.password)
            return key_obj
        else:
            return None

    @property
    def private_key_file(self):
        if not self.private_key_obj:
            return None
        project_dir = settings.PROJECT_DIR
        tmp_dir = os.path.join(project_dir, 'tmp')
        key_name = '.' + md5(self.private_key.encode('utf-8')).hexdigest()
        key_path = os.path.join(tmp_dir, key_name)
        if not os.path.exists(key_path):
            self.private_key_obj.write_private_key_file(key_path)
            os.chmod(key_path, 0o400)
        return key_path

    def get_private_key(self):
        if not self.private_key_obj:
            return None
        string_io = io.StringIO()
        self.private_key_obj.write_private_key(string_io)
        private_key = string_io.getvalue()
        return private_key

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

    def has_special_auth(self, asset=None, username=None):
        from .authbook import AuthBook
        if username is None:
            username = self.username
        queryset = AuthBook.objects.filter(username=username)
        if asset:
            queryset = queryset.filter(asset=asset)
        return queryset.exists()

    def get_asset_user(self, asset, username=None):
        from ..backends import AssetUserManager
        if username is None:
            username = self.username
        try:
            manager = AssetUserManager()
            other = manager.get_latest(
                username=username, asset=asset,
                prefer_id=self.id, prefer=self._prefer,
            )
            return other
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def load_asset_special_auth(self, asset=None, username=None):
        if not asset:
            return self

        instance = self.get_asset_user(asset, username=username)
        if instance:
            self._merge_auth(instance)

    def _merge_auth(self, other):
        if other.password:
            self.password = other.password
        if other.public_key or other.private_key:
            self.private_key = other.private_key
            self.public_key = other.public_key

    def clear_auth(self):
        self.password = ''
        self.private_key = ''
        self.public_key = ''
        self.save()

    @staticmethod
    def gen_password():
        return str(uuid.uuid4())

    @staticmethod
    def gen_key(username):
        private_key, public_key = ssh_key_gen(
            username=username
        )
        return private_key, public_key

    def auto_gen_auth(self, password=True, key=True):
        _password = None
        _private_key = None
        _public_key = None

        if password:
            _password = self.gen_password()
        if key:
            _private_key, _public_key = self.gen_key(self.username)
        self.set_auth(
            password=_password, private_key=_private_key,
            public_key=_public_key
        )


class BaseUser(OrgModelMixin, AuthMixin, ConnectivityMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    username = models.CharField(max_length=128, blank=True, verbose_name=_('Username'), validators=[alphanumeric], db_index=True)
    password = fields.EncryptCharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    private_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH private key'))
    public_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH public key'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    ASSETS_AMOUNT_CACHE_KEY = "ASSET_USER_{}_ASSETS_AMOUNT"
    ASSET_USER_CACHE_TIME = 600

    _prefer = "system_user"

    def get_related_assets(self):
        assets = self.assets.filter(org_id=self.org_id)
        return assets

    def get_username(self):
        return self.username

    @lazyproperty
    def assets_amount(self):
        cache_key = self.ASSETS_AMOUNT_CACHE_KEY.format(self.id)
        cached = cache.get(cache_key)
        if not cached:
            cached = self.get_related_assets().count()
            cache.set(cache_key, cached, self.ASSET_USER_CACHE_TIME)
        return cached

    def expire_assets_amount(self):
        cache_key = self.ASSETS_AMOUNT_CACHE_KEY.format(self.id)
        cache.delete(cache_key)

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

