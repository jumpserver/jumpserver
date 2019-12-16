#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import uuid
import base64
import string
import random

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models

from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.shortcuts import reverse

from orgs.utils import current_org
from common.utils import get_signer, date_expired_default, get_logger, lazyproperty
from common import fields
from ..signals import post_user_change_password


__all__ = ['User']

signer = get_signer()

logger = get_logger(__file__)


class AuthMixin:
    @property
    def password_raw(self):
        raise AttributeError('Password raw is not a readable attribute')

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
            self.date_password_last_updated = timezone.now()
            post_user_change_password.send(self.__class__, user=self)
            super().set_password(raw_password)

    def can_update_password(self):
        return self.is_local

    def can_update_ssh_key(self):
        return self.can_use_ssh_key_login()

    def can_use_ssh_key_login(self):
        return settings.TERMINAL_PUBLIC_KEY_AUTH

    def is_public_key_valid(self):
        """
            Check if the user's ssh public key is valid.
            This function is used in base.html.
        """
        if self.public_key:
            return True
        return False

    @property
    def public_key_obj(self):
        class PubKey(object):
            def __getattr__(self, item):
                return ''

        if self.public_key:
            import sshpubkeys
            try:
                return sshpubkeys.SSHKey(self.public_key)
            except (TabError, TypeError):
                pass
        return PubKey()

    def reset_password(self, new_password):
        self.set_password(new_password)
        self.save()

    @property
    def date_password_expired(self):
        interval = settings.SECURITY_PASSWORD_EXPIRATION_TIME
        date_expired = self.date_password_last_updated + timezone.timedelta(
            days=int(interval))
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

    def get_login_confirm_setting(self):
        if hasattr(self, 'login_confirm_setting'):
            s = self.login_confirm_setting
            if s.reviewers.all().count() and s.is_active:
                return s
        return False

    @staticmethod
    def get_public_key_body(key):
        for i in key.split():
            if len(i) > 256:
                return i
        return key

    def check_public_key(self, key):
        if not self.public_key:
            return False
        key = self.get_public_key_body(key)
        key_saved = self.get_public_key_body(self.public_key)
        if key == key_saved:
            return True
        else:
            return False


class RoleMixin:
    ROLE_ADMIN = 'Admin'
    ROLE_USER = 'User'
    ROLE_APP = 'App'
    ROLE_AUDITOR = 'Auditor'

    ROLE_CHOICES = (
        (ROLE_ADMIN, _('Administrator')),
        (ROLE_USER, _('User')),
        (ROLE_APP, _('Application')),
        (ROLE_AUDITOR, _("Auditor"))
    )
    role = ROLE_USER

    @property
    def role_display(self):
        if not current_org.is_real():
            return self.get_role_display()
        roles = []
        if self in current_org.get_org_admins():
            roles.append(str(_('Org admin')))
        if self in current_org.get_org_auditors():
            roles.append(str(_('Org auditor')))
        if self in current_org.get_org_users():
            roles.append(str(_('User')))
        return " | ".join(roles)

    @property
    def is_superuser(self):
        if self.role == 'Admin':
            return True
        else:
            return False

    @is_superuser.setter
    def is_superuser(self, value):
        if value is True:
            self.role = 'Admin'
        else:
            self.role = 'User'

    @property
    def is_super_auditor(self):
        return self.role == 'Auditor'

    @property
    def is_common_user(self):
        if self.is_org_admin:
            return False
        if self.is_org_auditor:
            return False
        if self.is_app:
            return False
        return True

    @property
    def is_app(self):
        return self.role == 'App'

    @lazyproperty
    def user_orgs(self):
        from orgs.models import Organization
        return Organization.get_user_user_orgs(self)

    @lazyproperty
    def admin_orgs(self):
        from orgs.models import Organization
        return Organization.get_user_admin_orgs(self)

    @lazyproperty
    def audit_orgs(self):
        from orgs.models import Organization
        return Organization.get_user_audit_orgs(self)

    @lazyproperty
    def admin_or_audit_orgs(self):
        from orgs.models import Organization
        return Organization.get_user_admin_or_audit_orgs(self)

    @lazyproperty
    def is_org_admin(self):
        if self.is_superuser or self.related_admin_orgs.exists():
            return True
        else:
            return False

    @lazyproperty
    def is_org_auditor(self):
        if self.is_super_auditor or self.related_audit_orgs.exists():
            return True
        else:
            return False

    @lazyproperty
    def can_admin_current_org(self):
        return current_org.can_admin_by(self)

    @lazyproperty
    def can_audit_current_org(self):
        return current_org.can_audit_by(self)

    @lazyproperty
    def can_user_current_org(self):
        return current_org.can_user_by(self)

    @lazyproperty
    def can_admin_or_audit_current_org(self):
        return self.can_admin_current_org or self.can_audit_current_org

    @property
    def is_staff(self):
        if self.is_authenticated and self.is_valid:
            return True
        else:
            return False

    @is_staff.setter
    def is_staff(self, value):
        pass

    @classmethod
    def create_app_user(cls, name, comment):
        app = cls.objects.create(
            username=name, name=name, email='{}@local.domain'.format(name),
            is_active=False, role='App', comment=comment,
            is_first_login=False, created_by='System'
        )
        access_key = app.create_access_key()
        return app, access_key

    def remove(self):
        if not current_org.is_real():
            return
        if self.can_user_current_org:
            current_org.users.remove(self)
        if self.can_admin_current_org:
            current_org.admins.remove(self)
        if self.can_audit_current_org:
            current_org.auditors.remove(self)


class TokenMixin:
    CACHE_KEY_USER_RESET_PASSWORD_PREFIX = "_KEY_USER_RESET_PASSWORD_{}"
    email = ''
    id = None

    @property
    def private_token(self):
        return self.create_private_token()

    def create_private_token(self):
        from authentication.models import PrivateToken
        token, created = PrivateToken.objects.get_or_create(user=self)
        return token

    def delete_private_token(self):
        from authentication.models import PrivateToken
        PrivateToken.objects.filter(user=self).delete()

    def refresh_private_token(self):
        self.delete_private_token()
        return self.create_private_token()

    def create_bearer_token(self, request=None):
        expiration = settings.TOKEN_EXPIRATION or 3600
        if request:
            remote_addr = request.META.get('REMOTE_ADDR', '')
        else:
            remote_addr = '0.0.0.0'
        if not isinstance(remote_addr, bytes):
            remote_addr = remote_addr.encode("utf-8")
        remote_addr = base64.b16encode(remote_addr)  # .replace(b'=', '')
        cache_key = '%s_%s' % (self.id, remote_addr)
        token = cache.get(cache_key)
        if not token:
            token = uuid.uuid4().hex
        cache.set(token, self.id, expiration)
        cache.set('%s_%s' % (self.id, remote_addr), token, expiration)
        date_expired = timezone.now() + timezone.timedelta(seconds=expiration)
        return token, date_expired

    def refresh_bearer_token(self, token):
        pass

    def create_access_key(self):
        access_key = self.access_keys.create()
        return access_key

    @property
    def access_key(self):
        return self.access_keys.first()

    def generate_reset_token(self):
        letter = string.ascii_letters + string.digits
        token = ''.join([random.choice(letter) for _ in range(50)])
        self.set_cache(token)
        return token

    @classmethod
    def validate_reset_password_token(cls, token):
        try:
            key = cls.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
            value = cache.get(key)
            user_id = value.get('id', '')
            email = value.get('email', '')
            user = cls.objects.get(id=user_id, email=email)
        except (AttributeError, cls.DoesNotExist) as e:
            logger.error(e, exc_info=True)
            user = None
        return user

    def set_cache(self, token):
        key = self.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        cache.set(key, {'id': self.id, 'email': self.email}, 3600)

    @classmethod
    def expired_reset_password_token(cls, token):
        key = cls.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        cache.delete(key)


class MFAMixin:
    mfa_level = 0
    otp_secret_key = ''
    MFA_LEVEL_CHOICES = (
        (0, _('Disable')),
        (1, _('Enable')),
        (2, _("Force enable")),
    )

    @property
    def mfa_enabled(self):
        return self.mfa_force_enabled or self.mfa_level > 0

    @property
    def mfa_force_enabled(self):
        if settings.SECURITY_MFA_AUTH:
            return True
        return self.mfa_level == 2

    def enable_mfa(self):
        if not self.mfa_level == 2:
            self.mfa_level = 1

    def force_enable_mfa(self):
        self.mfa_level = 2

    def disable_mfa(self):
        self.mfa_level = 0
        self.otp_secret_key = None

    def reset_mfa(self):
        if self.mfa_is_otp():
            self.otp_secret_key = ''

    @staticmethod
    def mfa_is_otp():
        if settings.OTP_IN_RADIUS:
            return False
        return True

    def check_radius(self, code):
        from authentication.backends.radius import RadiusBackend
        backend = RadiusBackend()
        user = backend.authenticate(None, username=self.username, password=code)
        if user:
            return True
        return False

    def check_otp(self, code):
        from ..utils import check_otp_code
        return check_otp_code(self.otp_secret_key, code)

    def check_mfa(self, code):
        if settings.OTP_IN_RADIUS:
            return self.check_radius(code)
        else:
            return self.check_otp(code)

    def mfa_enabled_but_not_set(self):
        if self.mfa_enabled and \
                self.mfa_is_otp() and \
                not self.otp_secret_key:
            return True
        return False


class User(AuthMixin, TokenMixin, RoleMixin, MFAMixin, AbstractUser):
    SOURCE_LOCAL = 'local'
    SOURCE_LDAP = 'ldap'
    SOURCE_OPENID = 'openid'
    SOURCE_RADIUS = 'radius'
    SOURCE_CHOICES = (
        (SOURCE_LOCAL, _('Local')),
        (SOURCE_LDAP, 'LDAP/AD'),
        (SOURCE_OPENID, 'OpenID'),
        (SOURCE_RADIUS, 'Radius'),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    username = models.CharField(
        max_length=128, unique=True, verbose_name=_('Username')
    )
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    email = models.EmailField(
        max_length=128, unique=True, verbose_name=_('Email')
    )
    groups = models.ManyToManyField(
        'users.UserGroup', related_name='users',
        blank=True, verbose_name=_('User group')
    )
    role = models.CharField(
        choices=RoleMixin.ROLE_CHOICES, default='User', max_length=10,
        blank=True, verbose_name=_('Role')
    )
    avatar = models.ImageField(
        upload_to="avatar", null=True, verbose_name=_('Avatar')
    )
    wechat = models.CharField(
        max_length=128, blank=True, verbose_name=_('Wechat')
    )
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_('Phone')
    )
    mfa_level = models.SmallIntegerField(
        default=0, choices=MFAMixin.MFA_LEVEL_CHOICES, verbose_name=_('MFA')
    )
    otp_secret_key = fields.EncryptCharField(max_length=128, blank=True, null=True)
    # Todo: Auto generate key, let user download
    private_key = fields.EncryptTextField(
        blank=True, null=True, verbose_name=_('Private key')
    )
    public_key = fields.EncryptTextField(
        blank=True, null=True, verbose_name=_('Public key')
    )
    comment = models.TextField(
        blank=True, null=True, verbose_name=_('Comment')
    )
    is_first_login = models.BooleanField(default=True)
    date_expired = models.DateTimeField(
        default=date_expired_default, blank=True, null=True,
        db_index=True, verbose_name=_('Date expired')
    )
    created_by = models.CharField(
        max_length=30, default='', blank=True, verbose_name=_('Created by')
    )
    source = models.CharField(
        max_length=30, default=SOURCE_LOCAL, choices=SOURCE_CHOICES,
        verbose_name=_('Source')
    )
    date_password_last_updated = models.DateTimeField(
        auto_now_add=True, blank=True, null=True,
        verbose_name=_('Date password last updated')
    )

    user_cache_key_prefix = '_User_{}'

    def __str__(self):
        return '{0.name}({0.username})'.format(self)

    def get_absolute_url(self):
        return reverse('users:user-detail', args=(self.id,))

    @property
    def groups_display(self):
        return ' '.join([group.name for group in self.groups.all()])

    @property
    def source_display(self):
        return self.get_source_display()

    @property
    def is_expired(self):
        if self.date_expired and self.date_expired < timezone.now():
            return True
        else:
            return False

    @property
    def expired_remain_days(self):
        date_remain = self.date_expired - timezone.now()
        return date_remain.days

    @property
    def will_expired(self):
        if 0 <= self.expired_remain_days < 5:
            return True
        else:
            return False

    @property
    def is_valid(self):
        if self.is_active and not self.is_expired:
            return True
        return False

    @property
    def is_local(self):
        return self.source == self.SOURCE_LOCAL

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.username
        if self.username == 'admin':
            self.role = 'Admin'
            self.is_active = True
        super().save(*args, **kwargs)

    def is_member_of(self, user_group):
        if user_group in self.groups.all():
            return True
        return False

    def set_avatar(self, f):
        self.avatar.save(self.username, f)

    def avatar_url(self):
        admin_default = settings.STATIC_URL + "img/avatar/admin.png"
        user_default = settings.STATIC_URL + "img/avatar/user.png"
        if self.avatar:
            return self.avatar.url
        if self.is_superuser:
            return admin_default
        else:
            return user_default

    def delete(self, using=None, keep_parents=False):
        if self.pk == 1 or self.username == 'admin':
            return
        return super(User, self).delete()

    class Meta:
        ordering = ['username']
        verbose_name = _("User")

    #: Use this method initial user
    @classmethod
    def initial(cls):
        from .group import UserGroup
        user = cls(username='admin',
                   email='admin@jumpserver.org',
                   name=_('Administrator'),
                   password_raw='admin',
                   role='Admin',
                   comment=_('Administrator is the super user of system'),
                   created_by=_('System'))
        user.save()
        user.groups.add(UserGroup.initial())

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError
        from .group import UserGroup

        seed()
        for i in range(count):
            user = cls(username=forgery_py.internet.user_name(True),
                       email=forgery_py.internet.email_address(),
                       name=forgery_py.name.full_name(),
                       password=make_password(forgery_py.lorem_ipsum.word()),
                       role=choice(list(dict(User.ROLE_CHOICES).keys())),
                       wechat=forgery_py.internet.user_name(True),
                       comment=forgery_py.lorem_ipsum.sentence(),
                       created_by=choice(cls.objects.all()).username)
            try:
                user.save()
            except IntegrityError:
                print('Duplicate Error, continue ...')
                continue
            user.groups.add(choice(UserGroup.objects.all()))
            user.save()
