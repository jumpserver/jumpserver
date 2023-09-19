# -*- coding: utf-8 -*-
#
import os
from hashlib import md5

import sshpubkeys
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from accounts.const import SecretType, SecretStrategy
from accounts.models.mixins import VaultModelMixin, VaultManagerMixin, VaultQuerySetMixin
from accounts.utils import SecretGenerator
from common.db import fields
from common.utils import (
    ssh_key_string_to_obj, ssh_key_gen, get_logger,
    random_string, lazyproperty, parse_ssh_public_key_str, is_openssh_format_key
)
from orgs.mixins.models import JMSOrgBaseModel, OrgManager

logger = get_logger(__file__)


class BaseAccountQuerySet(VaultQuerySetMixin, models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class BaseAccountManager(VaultManagerMixin, OrgManager):
    def active(self):
        return self.get_queryset().active()


class SecretWithRandomMixin(models.Model):
    secret_type = models.CharField(
        choices=SecretType.choices, max_length=16,
        default=SecretType.PASSWORD, verbose_name=_('Secret type')
    )
    secret = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Secret'))
    secret_strategy = models.CharField(
        choices=SecretStrategy.choices, max_length=16,
        default=SecretStrategy.custom, verbose_name=_('Secret strategy')
    )
    password_rules = models.JSONField(default=dict, verbose_name=_('Password rules'))

    class Meta:
        abstract = True

    @lazyproperty
    def secret_generator(self):
        return SecretGenerator(
            self.secret_strategy, self.secret_type,
            self.password_rules,
        )

    def get_secret(self):
        if self.secret_strategy == 'random':
            return self.secret_generator.get_secret()
        else:
            return self.secret


class BaseAccount(VaultModelMixin, JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    username = models.CharField(max_length=128, blank=True, verbose_name=_('Username'), db_index=True)
    secret_type = models.CharField(
        max_length=16, choices=SecretType.choices, default=SecretType.PASSWORD, verbose_name=_('Secret type')
    )
    privileged = models.BooleanField(verbose_name=_("Privileged"), default=False)
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    objects = BaseAccountManager.from_queryset(BaseAccountQuerySet)()

    @property
    def has_secret(self):
        return bool(self.secret)

    @property
    def has_username(self):
        return bool(self.username)

    @property
    def spec_info(self):
        data = {}
        if self.secret_type != SecretType.SSH_KEY:
            return data
        data['ssh_key_fingerprint'] = self.ssh_key_fingerprint
        return data

    @property
    def password(self):
        if self.secret_type == SecretType.PASSWORD:
            return self.secret
        return None

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
        if self.secret_type == SecretType.SSH_KEY and self.private_key:
            return parse_ssh_public_key_str(self.private_key)
        return None

    @property
    def ssh_key_fingerprint(self):
        if self.public_key:
            public_key = self.public_key
        elif self.private_key:
            try:
                public_key = parse_ssh_public_key_str(self.private_key)
            except IOError as e:
                return str(e)
        else:
            return ''

        if not public_key:
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
        if self.secret_type != SecretType.SSH_KEY \
                or not self.secret \
                or not self.private_key:
            return None
        project_dir = settings.PROJECT_DIR
        tmp_dir = os.path.join(project_dir, 'tmp')
        key_name = '.' + md5(self.private_key.encode('utf-8')).hexdigest()
        key_path = os.path.join(tmp_dir, key_name)
        if not os.path.exists(key_path):
            # https://github.com/ansible/ansible-runner/issues/544
            # ssh requires OpenSSH format keys to have a full ending newline.
            # It does not require this for old-style PEM keys.
            with open(key_path, 'w') as f:
                f.write(self.secret)
                if is_openssh_format_key(self.secret.encode('utf-8')):
                    f.write("\n")
            os.chmod(key_path, 0o400)
        return key_path

    def get_private_key(self):
        if not self.private_key:
            return None
        return self.private_key

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
