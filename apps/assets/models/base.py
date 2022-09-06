# -*- coding: utf-8 -*-
#
import io
import os
import uuid
from hashlib import md5

import sshpubkeys
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db.models import QuerySet

from common.utils import (
    ssh_key_string_to_obj, ssh_key_gen, get_logger,
    random_string, ssh_pubkey_gen,
)
from common.db import fields
from orgs.mixins.models import OrgModelMixin


logger = get_logger(__file__)


class Connectivity(models.TextChoices):
    unknown = 'unknown', _('Unknown')
    ok = 'ok', _('Ok')
    failed = 'failed', _('Failed')


class AbsConnectivity(models.Model):
    connectivity = models.CharField(
        choices=Connectivity.choices, default=Connectivity.unknown,
        max_length=16, verbose_name=_('Connectivity')
    )
    date_verified = models.DateTimeField(null=True, verbose_name=_("Date verified"))

    def set_connectivity(self, val):
        self.connectivity = val
        self.date_verified = timezone.now()
        self.save(update_fields=['connectivity', 'date_verified'])

    @classmethod
    def bulk_set_connectivity(cls, queryset_or_id, connectivity):
        if not isinstance(queryset_or_id, QuerySet):
            queryset = cls.objects.filter(id__in=queryset_or_id)
        else:
            queryset = queryset_or_id
        queryset.update(connectivity=connectivity, date_verified=timezone.now())

    class Meta:
        abstract = True


class BaseAccount(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    username = models.CharField(max_length=128, blank=True, verbose_name=_('Username'), db_index=True)
    password = fields.EncryptCharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    private_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH private key'))
    public_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH public key'))
    token = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Token'))
    privileged = models.BooleanField(verbose_name=_("Privileged account"), default=False)
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    ASSETS_AMOUNT_CACHE_KEY = "ASSET_USER_{}_ASSETS_AMOUNT"
    ASSET_USER_CACHE_TIME = 600

    APPS_AMOUNT_CACHE_KEY = "APP_USER_{}_APPS_AMOUNT"
    APP_USER_CACHE_TIME = 600

    def expire_assets_amount(self):
        cache_key = self.ASSETS_AMOUNT_CACHE_KEY.format(self.id)
        cache.delete(cache_key)

    @property
    def ssh_key_fingerprint(self):
        if self.public_key:
            public_key = self.public_key
        elif self.private_key:
            try:
                public_key = ssh_pubkey_gen(private_key=self.private_key, password=self.password)
            except IOError as e:
                return str(e)
        else:
            return ''

        public_key_obj = sshpubkeys.SSHKey(public_key)
        fingerprint = public_key_obj.hash_md5()
        return fingerprint

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

    def set_auth(self, **kwargs):
        update_fields = []
        for k, v in kwargs.items():
            setattr(self, k, v)
            update_fields.append(k)
        if update_fields:
            self.save(update_fields=update_fields)

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
        self.token = ''
        self.save()

    @staticmethod
    def gen_password(length=36):
        return random_string(length, special_char=True)

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

    def _to_secret_json(self):
        """Push system user use it"""
        return {
            'name': self.name,
            'username': self.username,
            'password': self.password,
            'public_key': self.public_key,
            'private_key': self.private_key_file,
            'token': self.token
        }

    class Meta:
        abstract = True

