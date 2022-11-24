# -*- coding: utf-8 -*-
#
import io
import os
import sshpubkeys
from hashlib import md5

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import QuerySet
from django.utils.translation import ugettext_lazy as _

from common.utils import (
    ssh_key_string_to_obj, ssh_key_gen, get_logger,
    random_string, ssh_pubkey_gen, lazyproperty
)
from common.db import fields
from orgs.mixins.models import JMSOrgBaseModel
from assets.const import Connectivity, SecretType

logger = get_logger(__file__)


class AbsConnectivity(models.Model):
    connectivity = models.CharField(
        choices=Connectivity.choices, default=Connectivity.UNKNOWN,
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


class BaseAccount(JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    username = models.CharField(max_length=128, blank=True, verbose_name=_('Username'), db_index=True)
    secret_type = models.CharField(
        max_length=16, choices=SecretType.choices, default=SecretType.PASSWORD, verbose_name=_('Secret type')
    )
    secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Secret'))
    privileged = models.BooleanField(verbose_name=_("Privileged"), default=False)
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    @property
    def has_secret(self):
        return bool(self.secret)

    @property
    def has_username(self):
        return bool(self.username)

    @property
    def specific(self):
        data = {}
        if self.secret_type != SecretType.SSH_KEY:
            return data
        data['ssh_key_fingerprint'] = self.ssh_key_fingerprint
        return data

    @property
    def private_key(self):
        if self.secret_type == SecretType.SSH_KEY:
            return self.secret
        return None

    @private_key.setter
    def private_key(self, value):
        self.secret = value
        self.secret_type = SecretType.SSH_KEY

    @lazyproperty
    def public_key(self):
        if self.secret_type == SecretType.SSH_KEY:
            return ssh_pubkey_gen(private_key=self.private_key)
        return None

    @property
    def ssh_key_fingerprint(self):
        if self.public_key:
            public_key = self.public_key
        elif self.private_key:
            try:
                public_key = ssh_pubkey_gen(private_key=self.private_key)
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
            key_obj = ssh_key_string_to_obj(self.private_key)
            return key_obj
        else:
            return None

    @property
    def private_key_path(self):
        if not self.secret_type != SecretType.SSH_KEY or not self.secret:
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

    @staticmethod
    def gen_password(length=36):
        return random_string(length, special_char=True)

    @staticmethod
    def gen_key(username):
        private_key, public_key = ssh_key_gen(username=username)
        return private_key, public_key

    def _to_secret_json(self):
        """Push system user use it"""
        return {
            'name': self.name,
            'username': self.username,
            'public_key': self.public_key,
        }

    class Meta:
        abstract = True
