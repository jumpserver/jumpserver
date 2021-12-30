#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import uuid
import base64
import string
import random
import datetime
from typing import Callable

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.shortcuts import reverse

from orgs.utils import current_org
from orgs.models import Organization
from common.exceptions import JMSException
from common.utils import date_expired_default, get_logger, lazyproperty, random_string
from common import fields
from common.db.models import TextChoices
from users.exceptions import MFANotEnabled, PhoneNotSet
from ..signals import post_user_change_password

__all__ = ['User', 'UserPasswordHistory', 'MFAType']

logger = get_logger(__file__)


class MFAType(TextChoices):
    OTP = 'otp', _('One-time password')
    SMS_CODE = 'sms', _('SMS verify code')


class AuthMixin:
    date_password_last_updated: datetime.datetime
    is_local: bool
    set_password: Callable
    save: Callable
    history_passwords: models.Manager

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

    @staticmethod
    def can_use_ssh_key_login():
        return settings.TERMINAL_PUBLIC_KEY_AUTH

    def is_history_password(self, password):
        allow_history_password_count = settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT
        history_passwords = self.history_passwords.all() \
            .order_by('-date_created')[:int(allow_history_password_count)]

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
        self.need_update_password = False
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


class RoleManager(models.Manager):
    scope = None
    __cache = None

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    @property
    def display(self):
        roles = sorted(list(self.all()), key=lambda r: r.scope)
        roles_display = [role.name_display for role in roles]
        return ', '.join(roles_display)

    @property
    def role_bindings(self):
        from rbac.models import RoleBinding
        queryset = RoleBinding.objects.filter(user=self.user)
        if self.scope:
            queryset = queryset.filter(scope=self.scope)
        return queryset

    def get_queryset(self):
        if self.__cache is not None:
            return self.__cache
        from rbac.models import RoleBinding
        queryset = RoleBinding.get_user_roles(self.user)
        if self.scope:
            queryset = queryset.filter(scope=self.scope)
        return queryset

    def clear(self):
        if not self.scope:
            return
        return self.role_bindings.delete()

    def add(self, *roles):
        from rbac.models import RoleBinding
        items = []

        for role in roles:
            kwargs = {
                'role': role,
                'user': self.user,
                'scope': role.scope
            }
            if self.scope and role.scope != self.scope:
                continue
            if not current_org.is_root() and role.scope == RoleBinding.Scope.org:
                kwargs['org_id'] = current_org.id
            items.append(RoleBinding(**kwargs))

        try:
            RoleBinding.objects.bulk_create(items, ignore_conflicts=True)
        except Exception as e:
            logger.error('Create role binding error: {}'.format(e))

    def set(self, roles):
        self.clear()
        self.add(*roles)

    def cache_set(self, roles):
        self.__cache = roles


class OrgRoleManager(RoleManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from rbac.const import Scope
        self.scope = Scope.org


class SystemRoleManager(RoleManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from rbac.const import Scope
        self.scope = Scope.system


class RoleMixin:
    objects: models.Manager
    is_authenticated: bool
    is_valid: bool
    _org_roles = None
    _system_roles = None

    @lazyproperty
    def roles(self):
        return RoleManager(self)

    @lazyproperty
    def org_roles(self):
        return OrgRoleManager(self)

    @lazyproperty
    def system_roles(self):
        return SystemRoleManager(self)

    @lazyproperty
    def perms(self):
        return self.get_all_permissions()

    @lazyproperty
    def is_superuser(self):
        from rbac.builtin import BuiltinRole
        yes = self.system_roles.filter(
            name=BuiltinRole.system_admin.name
        ).exists()
        return yes

    @property
    def is_staff(self):
        return self.is_authenticated and self.is_valid

    @is_staff.setter
    def is_staff(self, value):
        pass

    @classmethod
    def create_app_user(cls, name, comment):
        from rbac.models import Role
        app = cls.objects.create(
            username=name, name=name, email='{}@local.domain'.format(name),
            is_active=False, comment=comment, is_first_login=False, created_by='System',
            is_app=True,
        )
        access_key = app.create_access_key()
        role = Role.BuiltinRole.system_app.get_role()
        app.system_roles.add(role)
        return app, access_key

    def remove(self):
        if current_org.is_root():
            return
        self.org_roles.clear()

    @classmethod
    def get_super_admins(cls):
        from rbac.models import Role, RoleBinding
        system_admin = Role.BuiltinRole.system_admin.get_role()
        return RoleBinding.get_role_users(system_admin)

    @classmethod
    def get_org_admins(cls, org=None):
        from rbac.models import Role, RoleBinding
        org_admin = Role.BuiltinRole.org_admin.get_role()
        return RoleBinding.get_role_users(org_admin)

    @classmethod
    def get_nature_users(cls):
        return cls.objects.filter(is_app=False)

    @classmethod
    def get_org_users(cls, org=None):
        from rbac.models import RoleBinding
        queryset = cls.objects.all()
        if org is None:
            org = current_org
        if not org.is_root():
            role_bindings = RoleBinding.objects.filter(org_id=org.id)
            user_ids = role_bindings.values_list('user', flat=True).distinct()
            queryset = cls.objects.filter(id__in=user_ids)
        return queryset

    def get_all_permissions(self):
        from rbac.models import RoleBinding
        perms = RoleBinding.get_user_perms(self)
        return perms


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
            token = random_string(36)
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
        if settings.SECURITY_MFA_AUTH in [True, 1]:
            return True
        if settings.SECURITY_MFA_AUTH == 2 and self.is_org_admin:
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

    def check_mfa(self, code, mfa_type=MFAType.OTP):
        if not self.mfa_enabled:
            raise MFANotEnabled

        if mfa_type == MFAType.OTP:
            if settings.OTP_IN_RADIUS:
                return self.check_radius(code)
            else:
                return self.check_otp(code)
        elif mfa_type == MFAType.SMS_CODE:
            return self.check_sms_code(code)

    def get_supported_mfa_types(self):
        methods = []
        if self.otp_secret_key:
            methods.append(MFAType.OTP)
        if settings.XPACK_ENABLED and settings.SMS_ENABLED and self.phone:
            methods.append(MFAType.SMS_CODE)
        return methods

    def check_sms_code(self, code):
        from authentication.sms_verify_code import VerifyCodeUtil

        if not self.phone:
            raise PhoneNotSet

        try:
            util = VerifyCodeUtil(self.phone)
            return util.verify(code)
        except JMSException:
            return False

    def send_sms_code(self):
        from authentication.sms_verify_code import VerifyCodeUtil

        if not self.phone:
            raise PhoneNotSet

        util = VerifyCodeUtil(self.phone)
        util.touch()
        return util.timeout

    def mfa_enabled_but_not_set(self):
        if not self.mfa_enabled:
            return False, None

        if not self.mfa_is_otp():
            return False, None

        if self.mfa_is_otp() and self.otp_secret_key:
            return False, None

        if self.phone and settings.SMS_ENABLED and settings.XPACK_ENABLED:
            return False, None

        return True, reverse('authentication:user-otp-enable-start')


class User(AuthMixin, TokenMixin, RoleMixin, MFAMixin, AbstractUser):
    class Source(TextChoices):
        local = 'local', _('Local')
        ldap = 'ldap', 'LDAP/AD'
        openid = 'openid', 'OpenID'
        radius = 'radius', 'Radius'
        cas = 'cas', 'CAS'

    SOURCE_BACKEND_MAPPING = {
        Source.local: [
            settings.AUTH_BACKEND_MODEL, settings.AUTH_BACKEND_PUBKEY,
            settings.AUTH_BACKEND_WECOM, settings.AUTH_BACKEND_DINGTALK,
        ],
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
        default='User', max_length=10,
        blank=True, verbose_name=_('Role')
    )
    is_app = models.BooleanField(default=False)
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
    need_update_password = models.BooleanField(
        default=False, verbose_name=_('Need update password')
    )
    wecom_id = models.CharField(null=True, default=None, unique=True, max_length=128, verbose_name=_('WeCom'))
    dingtalk_id = models.CharField(null=True, default=None, unique=True, max_length=128, verbose_name=_('DingTalk'))
    feishu_id = models.CharField(null=True, default=None, unique=True, max_length=128, verbose_name=_('FeiShu'))

    def __str__(self):
        return '{0.name}({0.username})'.format(self)

    @classmethod
    def get_group_ids_by_user_id(cls, user_id):
        group_ids = cls.groups.through.objects.filter(user_id=user_id)\
            .distinct().values_list('usergroup_id', flat=True)
        group_ids = list(group_ids)
        return group_ids

    @property
    def receive_backends(self):
        return self.user_msg_subscription.receive_backends

    @property
    def is_wecom_bound(self):
        return bool(self.wecom_id)

    @property
    def is_dingtalk_bound(self):
        return bool(self.dingtalk_id)

    @property
    def is_feishu_bound(self):
        return bool(self.feishu_id)

    @property
    def is_otp_secret_key_bound(self):
        return bool(self.otp_secret_key)

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
        return super().save(*args, **kwargs)

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

    def avatar_url(self):
        admin_default = settings.STATIC_URL + "img/avatar/admin.png"
        user_default = settings.STATIC_URL + "img/avatar/user.png"
        if self.avatar:
            return self.avatar.url
        if self.is_superuser:
            return admin_default
        else:
            return user_default

    def unblock_login(self):
        from users.utils import LoginBlockUtil, MFABlockUtils
        LoginBlockUtil.unblock_user(self.username)
        MFABlockUtils.unblock_user(self.username)

    @property
    def login_blocked(self):
        from users.utils import LoginBlockUtil, MFABlockUtils
        if LoginBlockUtil.is_user_block(self.username):
            return True
        if MFABlockUtils.is_user_block(self.username):
            return True

        return False

    def delete(self, using=None, keep_parents=False):
        if self.pk == 1 or self.username == 'admin':
            return
        return super(User, self).delete()

    def has_perm(self, perm, obj=None):
        has_perm = super().has_perm(perm, obj=obj)
        print("has perm: {}".format(has_perm))
        return has_perm

    @classmethod
    def get_user_allowed_auth_backends(cls, username):
        if not settings.ONLY_ALLOW_AUTH_FROM_SOURCE or not username:
            # return settings.AUTHENTICATION_BACKENDS
            return None
        user = cls.objects.filter(username=username).first()
        if not user:
            return None
        return user.get_allowed_auth_backends()

    def get_allowed_auth_backends(self):
        if not settings.ONLY_ALLOW_AUTH_FROM_SOURCE:
            return None
        return self.SOURCE_BACKEND_MAPPING.get(self.source, [])

    @property
    def belongs_orgs(self):
        if self.is_superuser:
            orgs = [Organization.root()] + list(Organization.objects.all())
        else:
            orgs = list(self.orgs.all())
        return orgs

    class Meta:
        ordering = ['username']
        verbose_name = _("User")
        permissions = [
            ('invite', _('Can invite user')),
            ('remove', _('Can remove user'))
        ]

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


class UserPasswordHistory(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    password = models.CharField(max_length=128)
    user = models.ForeignKey("users.User", related_name='history_passwords',
                             on_delete=models.CASCADE, verbose_name=_('User'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))

    def __str__(self):
        return f'{self.user} set at {self.date_created}'

    def __repr__(self):
        return self.__str__()

    class Meta:
        verbose_name = _("User password history")
