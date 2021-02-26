#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import uuid
import base64
import string
import random

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models
from django.db.models import TextChoices

from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.shortcuts import reverse

from orgs.utils import current_org
from orgs.models import OrganizationMember, Organization
from common.utils import date_expired_default, get_logger, lazyproperty
from common import fields
from common.const import choices
from common.db.models import ChoiceSet
from users.exceptions import MFANotEnabled
from ..signals import post_user_change_password


__all__ = ['User']

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

    def set_public_key(self, public_key):
        if self.can_update_ssh_key():
            self.public_key = public_key
            self.save()

    def can_update_password(self):
        return self.is_local

    def can_update_ssh_key(self):
        return self.can_use_ssh_key_login()

    def can_use_ssh_key_login(self):
        return self.is_local and settings.TERMINAL_PUBLIC_KEY_AUTH

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

    def get_public_key_comment(self):
        return self.public_key_obj.comment

    def get_public_key_hash_md5(self):
        if not callable(self.public_key_obj.hash_md5):
            return ''
        try:
            return self.public_key_obj.hash_md5()
        except:
            return ''

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
    class ROLE(ChoiceSet):
        ADMIN = choices.ADMIN, _('System administrator')
        AUDITOR = choices.AUDITOR, _('System auditor')
        USER = choices.USER, _('User')
        APP = 'App', _('Application')

    role = ROLE.USER

    @property
    def role_display(self):
        return self.get_role_display()

    @lazyproperty
    def org_roles(self):
        from orgs.models import ROLE as ORG_ROLE

        if not current_org.is_real():
            # 不是真实的组织，取 User 本身的角色
            if self.is_superuser:
                return [ORG_ROLE.ADMIN]
            else:
                return [ORG_ROLE.USER]

        # 是真实组织，取 OrganizationMember 中的角色
        roles = [
            org_member.role
            for org_member in self.m2m_org_members.all()
            if org_member.org_id == current_org.id
        ]
        roles.sort()
        return roles

    @lazyproperty
    def org_roles_label_list(self):
        from orgs.models import ROLE as ORG_ROLE
        return [str(ORG_ROLE[role]) for role in self.org_roles if role in ORG_ROLE]

    @lazyproperty
    def org_role_display(self):
        return ' | '.join(self.org_roles_label_list)

    @lazyproperty
    def total_role_display(self):
        roles = list({self.role_display, *self.org_roles_label_list})
        roles.sort()
        return ' | '.join(roles)

    def current_org_roles(self):
        from orgs.models import OrganizationMember, ROLE as ORG_ROLE
        if not current_org.is_real():
            if self.is_superuser:
                return [ORG_ROLE.ADMIN]
            else:
                return [ORG_ROLE.USER]

        roles = list(set(OrganizationMember.objects.filter(
            org_id=current_org.id, user=self
        ).values_list('role', flat=True)))

        return roles

    @property
    def is_superuser(self):
        if self.role == self.ROLE.ADMIN:
            return True
        else:
            return False

    @is_superuser.setter
    def is_superuser(self, value):
        if value is True:
            self.role = self.ROLE.ADMIN
        else:
            self.role = self.ROLE.USER

    @property
    def is_super_auditor(self):
        return self.role == self.ROLE.AUDITOR

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
        return self.role == self.ROLE.APP

    @lazyproperty
    def user_all_orgs(self):
        from orgs.models import Organization
        return Organization.get_user_all_orgs(self)

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
        from orgs.models import ROLE as ORG_ROLE
        if self.is_superuser or self.m2m_org_members.filter(role=ORG_ROLE.ADMIN).exists():
            return True
        else:
            return False

    @lazyproperty
    def is_org_auditor(self):
        from orgs.models import ROLE as ORG_ROLE
        if self.is_super_auditor or self.m2m_org_members.filter(role=ORG_ROLE.AUDITOR).exists():
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
            is_active=False, role=cls.ROLE.APP, comment=comment,
            is_first_login=False, created_by='System'
        )
        access_key = app.create_access_key()
        return app, access_key

    def remove(self):
        if not current_org.is_real():
            return
        org = Organization.get_instance(current_org.id)
        OrganizationMember.objects.remove_users(org, [self])

    @classmethod
    def get_super_admins(cls):
        return cls.objects.filter(role=cls.ROLE.ADMIN)

    @classmethod
    def get_org_admins(cls, org=None):
        from orgs.models import Organization
        if not isinstance(org, Organization):
            org = current_org
        org_admins = org.admins
        return org_admins

    @classmethod
    def get_super_and_org_admins(cls, org=None):
        super_admins = cls.get_super_admins()
        super_admins_id = list(super_admins.values_list('id', flat=True))
        org_admins = cls.get_org_admins(org)
        org_admins_id = list(org_admins.values_list('id', flat=True))
        admins_id = set(org_admins_id + super_admins_id)
        admins = User.objects.filter(id__in=admins_id)
        return admins


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
        if not token:
            return None
        key = cls.CACHE_KEY_USER_RESET_PASSWORD_PREFIX.format(token)
        value = cache.get(key)
        if not value:
            return None
        try:
            user_id = value.get('id', '')
            email = value.get('email', '')
            user = cls.objects.get(id=user_id, email=email)
            return user
        except (AttributeError, cls.DoesNotExist) as e:
            logger.error(e, exc_info=True)
            return None

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
        if not self.mfa_enabled:
            raise MFANotEnabled

        if settings.OTP_IN_RADIUS:
            return self.check_radius(code)
        else:
            return self.check_otp(code)

    def mfa_enabled_but_not_set(self):
        if not self.mfa_enabled:
            return False, None
        if self.mfa_is_otp() and not self.otp_secret_key:
            return True, reverse('authentication:user-otp-enable-start')
        return False, None


class User(AuthMixin, TokenMixin, RoleMixin, MFAMixin, AbstractUser):
    class Source(TextChoices):
        local = 'local', _('Local')
        ldap = 'ldap', 'LDAP/AD'
        openid = 'openid', 'OpenID'
        radius = 'radius', 'Radius'
        cas = 'cas', 'CAS'

    SOURCE_BACKEND_MAPPING = {
        Source.local: [settings.AUTH_BACKEND_MODEL, settings.AUTH_BACKEND_PUBKEY],
        Source.ldap: [settings.AUTH_BACKEND_LDAP],
        Source.openid: [settings.AUTH_BACKEND_OIDC_PASSWORD, settings.AUTH_BACKEND_OIDC_CODE],
        Source.radius: [settings.AUTH_BACKEND_RADIUS],
        Source.cas: [settings.AUTH_BACKEND_CAS],
    }

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
        choices=RoleMixin.ROLE.choices, default='User', max_length=10,
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
        max_length=30, default=Source.local,
        choices=Source.choices,
        verbose_name=_('Source')
    )
    date_password_last_updated = models.DateTimeField(
        auto_now_add=True, blank=True, null=True,
        verbose_name=_('Date password last updated')
    )

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
        return self.source == self.Source.local.value

    def set_unprovide_attr_if_need(self):
        if not self.name:
            self.name = self.username
        if not self.email or '@' not in self.email:
            email = '{}@{}'.format(self.username, settings.EMAIL_SUFFIX)
            if '@' in self.username:
                email = self.username
            self.email = email

    def save(self, *args, **kwargs):
        self.set_unprovide_attr_if_need()
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

    @classmethod
    def get_avatar_url(cls, username):
        user_default = settings.STATIC_URL + "img/avatar/user.png"
        return user_default

    # def admin_orgs(self):
    #     from orgs.models import Organization
    #     orgs = Organization.get_user_admin_or_audit_orgs(self)
    #     return orgs

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

    def can_send_created_mail(self):
        if self.email and self.source == self.Source.local.value:
            return True
        return False
