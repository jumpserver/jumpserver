#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import datetime
from typing import Callable

import sshpubkeys
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from common.utils import (
    get_logger,
    lazyproperty,
)
from users.signals import post_user_change_password
from users.exceptions import CreateSSHKeyExceedLimit

logger = get_logger(__file__)

__all__ = ['MFAMixin', 'AuthMixin']


class MFAMixin:
    mfa_level = 0
    otp_secret_key = ""
    MFA_LEVEL_CHOICES = (
        (0, _("Disabled")),
        (1, _("Enabled")),
        (2, _("Force enabled")),
    )
    is_org_admin: bool
    username: str
    phone: str

    @property
    def mfa_enabled(self):
        if self.mfa_force_enabled:
            return True
        return self.mfa_level > 0

    @property
    def mfa_force_enabled(self):
        force_level = settings.SECURITY_MFA_AUTH
        # 1 All users
        if force_level in [True, 1]:
            return True
        # 2 仅管理员强制开启
        if force_level == 2 and self.is_org_admin:
            return True
        # 3 仅用户开启
        return self.mfa_level == 2

    def enable_mfa(self):
        if not self.mfa_level == 2:
            self.mfa_level = 1

    def force_enable_mfa(self):
        self.mfa_level = 2

    def disable_mfa(self):
        self.mfa_level = 0

    def no_active_mfa(self):
        return len(self.active_mfa_backends) == 0

    @lazyproperty
    def active_mfa_backends(self):
        backends = self.get_user_mfa_backends(self)
        active_backends = [b for b in backends if b.is_active()]
        return active_backends

    @property
    def active_mfa_backends_mapper(self):
        return {b.name: b for b in self.active_mfa_backends}

    @staticmethod
    def get_user_mfa_backends(user):
        backends = []
        for cls in settings.MFA_BACKENDS:
            cls = import_string(cls)
            if cls.global_enabled():
                backends.append(cls(user))
        return backends

    def get_active_mfa_backend_by_type(self, mfa_type):
        backend = self.get_mfa_backend_by_type(mfa_type)
        if not backend or not backend.is_active():
            return None
        return backend

    def get_mfa_backend_by_type(self, mfa_type):
        mfa_mapper = {b.name: b for b in self.get_user_mfa_backends(self)}
        backend = mfa_mapper.get(mfa_type)
        if not backend:
            return None
        return backend


class AuthMixin:
    date_password_last_updated: datetime.datetime
    history_passwords: models.Manager
    need_update_password: bool
    public_key: str
    username: str
    is_local: bool
    set_password: Callable
    save: Callable
    history_passwords: models.Manager
    sect_cache_tpl = "user_sect_{}"
    id: str

    @property
    def password_raw(self):
        raise AttributeError("Password raw is not a readable attribute")

    #: Use this attr to set user object password, example
    #: user = User(username='example', password_raw='password', ...)
    #: It's equal:
    #: user = User(username='example', ...)
    #: user.set_password('password')
    @password_raw.setter
    def password_raw(self, password_raw_):
        self.set_password(password_raw_)

    def set_password(self, raw_password):
        if self.can_update_password():
            if self.username:
                self.date_password_last_updated = timezone.now()
                post_user_change_password.send(self.__class__, user=self)
            super().set_password(raw_password)  # noqa

    def set_ssh_key(self, name, public_key, private_key):
        if self.can_update_ssh_key():
            from authentication.models import SSHKey
            SSHKey.objects.create(name=name, public_key=public_key, private_key=private_key, user=self)
            post_user_change_password.send(self.__class__, user=self)

    def can_create_ssh_key(self):
        return self.ssh_keys.count() < settings.TERMINAL_SSH_KEY_LIMIT_COUNT

    def can_update_password(self):
        return self.is_local

    def can_update_ssh_key(self):
        return self.can_use_ssh_key_login()

    @staticmethod
    def can_use_ssh_key_login():
        return settings.TERMINAL_PUBLIC_KEY_AUTH

    def is_history_password(self, password):
        allow_history_password_count = settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT
        history_passwords = self.history_passwords.all().order_by("-date_created")[
                            : int(allow_history_password_count)
                            ]

        for history_password in history_passwords:
            if check_password(password, history_password.password):
                return True
        else:
            return False

    def is_public_key_valid(self):
        """
        Check if the user's ssh public key is valid.
        This function is used in base.html.
        """
        if self.user_ssh_keys:
            return True
        return False

    @property
    def public_key_obj(self):
        class PubKey(object):
            def __getattr__(self, item):
                return ""

        if self.public_key:
            try:
                return sshpubkeys.SSHKey(self.public_key)
            except (TabError, TypeError):
                pass
        return PubKey()

    def get_public_key_comment(self):
        return self.public_key_obj.comment

    def get_public_key_hash_md5(self):
        if not callable(self.public_key_obj.hash_md5):
            return ""
        try:
            return self.public_key_obj.hash_md5()
        except:
            return ""

    def reset_password(self, new_password):
        self.set_password(new_password)
        self.need_update_password = False
        self.save()

    @property
    def date_password_expired(self):
        interval = settings.SECURITY_PASSWORD_EXPIRATION_TIME
        date_expired = self.date_password_last_updated + timezone.timedelta(
            days=int(interval)
        )
        return date_expired

    @property
    def password_expired_remain_days(self):
        date_remain = self.date_password_expired - timezone.now()
        return date_remain.days

    @property
    def password_has_expired(self):
        if self.is_local and self.password_expired_remain_days < 0:
            return True
        return False

    @property
    def password_will_expired(self):
        if self.is_local and 0 <= self.password_expired_remain_days < 5:
            return True
        return False

    @staticmethod
    def get_public_key_md5(key):
        try:
            key_obj = sshpubkeys.SSHKey(key)
            return key_obj.hash_md5()
        except Exception as e:
            return ""

    @property
    def user_ssh_keys(self):
        return self.ssh_keys.filter(is_active=True).all()

    def check_public_key(self, key):
        key_md5 = self.get_public_key_md5(key)
        if not key_md5:
            return False
        for ssh_key in self.user_ssh_keys:
            self_key_md5 = self.get_public_key_md5(ssh_key.public_key)
            if key_md5 == self_key_md5:
                ssh_key.date_last_used = timezone.now()
                ssh_key.save(update_fields=['date_last_used'])
                return True
        return False

    def cache_login_password_if_need(self, password):
        from common.utils import signer

        if not settings.CACHE_LOGIN_PASSWORD_ENABLED:
            return
        backend = getattr(self, "backend", "")
        if backend.lower().find("ldap") < 0:
            return
        if not password:
            return
        key = self.sect_cache_tpl.format(self.id)
        ttl = settings.CACHE_LOGIN_PASSWORD_TTL
        if not isinstance(ttl, int) or ttl <= 0:
            return
        secret = signer.sign(password)
        cache.set(key, secret, ttl)

    def get_cached_password_if_has(self):
        from common.utils import signer

        if not settings.CACHE_LOGIN_PASSWORD_ENABLED:
            return ""
        key = self.sect_cache_tpl.format(self.id)
        secret = cache.get(key)
        if not secret:
            return ""
        password = signer.unsign(secret)
        return password
