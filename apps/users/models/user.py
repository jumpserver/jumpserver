#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import os

from collections import OrderedDict

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core import signing
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.shortcuts import reverse

from . import UserGroup
from common.utils import signer, date_expired_default
from django.db.models import Q

__all__ = ['User']


class User(AbstractUser):
    ROLE_CHOICES = (
        ('Admin', _('Administrator')),
        ('GroupAdmin', _('GroupAdministrator')),
        ('User', _('User')),
        ('App', _('Application'))
    )

    username = models.CharField(max_length=20, unique=True, verbose_name=_('Username'))
    name = models.CharField(max_length=20, verbose_name=_('Name'))
    email = models.EmailField(max_length=30, blank=True, verbose_name=_('Email'))
    groups = models.ManyToManyField(UserGroup, related_name='users', blank=True, verbose_name=_('User group'))
    managed_groups = models.ManyToManyField(UserGroup, related_name='managers', blank=True, verbose_name=_('Managed Group'))
    role = models.CharField(choices=ROLE_CHOICES, default='User', max_length=10, blank=True, verbose_name=_('Role'))
    avatar = models.ImageField(upload_to="avatar", null=True, verbose_name=_('Avatar'))
    wechat = models.CharField(max_length=30, blank=True, verbose_name=_('Wechat'))
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Phone'))
    enable_otp = models.BooleanField(default=False, verbose_name=_('Enable OTP'))
    secret_key_otp = models.CharField(max_length=16, blank=True)
    _private_key = models.CharField(max_length=5000, blank=True, verbose_name=_('ssh private key'))
    _public_key = models.CharField(max_length=5000, blank=True, verbose_name=_('ssh public key'))
    comment = models.TextField(max_length=200, blank=True, verbose_name=_('Comment'))
    is_first_login = models.BooleanField(default=True)
    date_expired = models.DateTimeField(default=date_expired_default, blank=True, null=True,
                                        verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=30, default='', verbose_name=_('Created by'))

    def __unicode__(self):
        return self.username
    __str__ = __unicode__

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

    def get_absolute_url(self):
        return reverse('users:user-detail', args=(self.id,))

    def is_public_key_valid(self):
        """
            Check if the user's ssh public key is valid.
            This function is used in base.html.
        """
        if self._public_key:
            return True
        return False

    @property
    def is_expired(self):
        if self.date_expired and self.date_expired < timezone.now():
            return True
        else:
            return False

    @property
    def is_valid(self):
        if self.is_active and not self.is_expired:
            return True
        return False

    @property
    def private_key(self):
        return signer.unsign(self._private_key)

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = signer.sign(private_key_raw)

    @property
    def public_key(self):
        return signer.unsign(self._public_key)

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = signer.sign(public_key_raw)

    @property
    def public_key_obj(self):
        class PubKey(object):
            def __getattr__(self, item):
                return ''
        if self.public_key:
            import sshpubkeys
            try:
                return sshpubkeys.SSHKey(self.public_key)
            except TabError:
                pass
        return PubKey()

    @property
    def is_superuser(self):
        return self.role == 'Admin'

    @is_superuser.setter
    def is_superuser(self, value):
        if value is True:
            self.role = 'Admin'
        else:
            self.role = 'User'

    @property
    def is_applier(self):
        return self.role in ['GroupAdmin', 'User']

    @property
    def is_admin(self):
        return self.role in ['GroupAdmin', 'Admin']

    @property
    def is_groupadmin(self):
        return self.role == 'GroupAdmin'

    @property
    def is_commonuser(self):
        return self.role == 'User'

    @property
    def is_app(self):
        return self.role == 'App'

    @property
    def is_staff(self):
        if self.is_authenticated and self.is_valid:
            return True
        else:
            return False

    @is_staff.setter
    def is_staff(self, value):
        pass

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.username

        super(User, self).save(*args, **kwargs)
        # Add the current user to the default group.
        if not self.groups.count():
            group = UserGroup.initial()
            self.groups.add(group)

    @property
    def private_token(self):
        return self.create_private_token

    @property
    def managed_users(self):
        if self.is_superuser:
            return User.objects.all()
        elif self.is_groupadmin:
            group_list = self.managed_groups.values_list('id',flat=True)
            return User.objects.filter(groups__id__in=list(group_list))
        else:
            return self

    @property
    def assets(self):
        from assets.models import Asset
        if self.is_superuser:
            return Asset.objects.all()
        elif self.is_groupadmin:
            return self.granted_assets_direct | \
                self.granted_assets_inherit_from_user_groups
        else:
            return self.granted_assets_direct

    @property
    def asset_groups(self):
        if self.is_superuser:
            from assets.models import AssetGroup
            return AssetGroup.objects.all()
        else:
            return self.created_asset_groups.all() | \
                self.granted_asset_groups_direct | \
                self.granted_asset_groups_inherit_from_user_groups

    @property
    def system_users(self):
        from assets.models import SystemUser
        asset_list = self.assets.values_list('id', flat=True)
        return SystemUser.objects.filter(assets__id__in=list(asset_list)).distinct()

    @property
    def can_apply_assets(self):
        from assets.models import Asset
        valid_assets = Asset.valid_assets()
        assets = Asset.objects.none()
        if self.is_groupadmin:
            return valid_assets
        elif self.is_commonuser:
            for manager in self.group_managers:
                assets |= manager.assets
        return assets

    @property
    def can_apply_asset_groups(self):
        from assets.models import AssetGroup
        if self.is_groupadmin:
            return AssetGroup.objects.filter(creater__role='Admin')
        elif self.is_commonuser:
            manager_list = self.group_managers.values_list('id', flat=True)
            return AssetGroup.objects.filter(creater__id__in=list(manager_list))
        return AssetGroup.objects.none()

    @property
    def can_apply_system_users(self):
        from assets.models import SystemUser
        system_users = SystemUser.objects.none()
        if self.is_groupadmin:
            return SystemUser.objects.all()
        elif self.is_commonuser:
            for manager in self.group_managers:
                system_users |= manager.system_users
        return system_users

    @property
    def group_managers(self):
        if self.is_commonuser:
            group_list = self.groups.values_list('id', flat=True)
            return User.objects.filter(
                role='GroupAdmin',
                groups__id__in=list(group_list))
        return User.objects.filter(role='Admin')

    @property
    def granted_assets_direct(self):
        from assets.models import Asset
        valid_assets = Asset.valid_assets()
        asset_perms_list = self.asset_permissions.filter(
            is_active=True,
            date_expired__gt=timezone.now(),
        ).values_list('id', flat=True)
        asset_group_list = self.granted_asset_groups_direct.values_list('id', flat=True)
        return valid_assets.filter(
            Q(granted_by_permissions__id__in=list(asset_perms_list)) |
            Q(groups__id__in=list(asset_group_list))
        ).distinct()

    @property
    def granted_assets_inherit_from_user_groups(self):
        from assets.models import Asset
        from perms.models import AssetPermission
        valid_assets = Asset.valid_assets()
        group_list = self.groups.values_list('id', flat=True)
        asset_perms_list = AssetPermission.valid_asset_perms().filter(
            user_groups__id__in=list(group_list)
        ).values_list('id', flat=True)
        asset_group_list = self.granted_asset_groups_inherit_from_user_groups \
            .values_list('id', flat=True)
        return valid_assets.filter(
            Q(granted_by_permissions__id__in=list(asset_perms_list)) |
            Q(groups__id__in=list(asset_group_list))
        ).distinct()

    @property
    def granted_asset_groups_direct(self):
        from assets.models import AssetGroup
        asset_perms_list = self.asset_permissions.values_list('id', flat=True)
        return AssetGroup.objects.filter(granted_by_permissions__id__in=list(asset_perms_list))

    @property
    def granted_asset_groups_inherit_from_user_groups(self):
        from assets.models import AssetGroup
        from perms.models import AssetPermission
        group_list= self.groups.values_list('id', flat=True)
        asset_perms_list = AssetPermission.valid_asset_perms().filter(
            user_groups__id__in=list(group_list)
        ).values_list('id', flat=True)
        return AssetGroup.objects.filter(granted_by_permissions__id__in=list(asset_perms_list))

    @property
    def create_private_token(self):
        from .authentication import PrivateToken
        try:
            token = PrivateToken.objects.get(user=self)
        except PrivateToken.DoesNotExist:
            token = PrivateToken.objects.create(user=self)
        return token.key

    def refresh_private_token(self):
        from .authentication import PrivateToken
        PrivateToken.objects.filter(user=self).delete()
        return PrivateToken.objects.create(user=self)

    def is_member_of(self, user_group):
        if user_group in self.groups.all():
            return True
        return False

    def check_public_key(self, public_key):
        if self.ssH_public_key == public_key:
            return True
        return False

    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        else:
            avatar_dir = os.path.join(settings.MEDIA_ROOT, 'avatar')
            if os.path.isdir(avatar_dir):
                return os.path.join(settings.MEDIA_URL, 'avatar', 'default.png')
        return 'https://www.gravatar.com/avatar/c6812ab450230979465d7bf288eadce2a?s=120&d=identicon'

    def generate_reset_token(self):
        return signer.sign_t({'reset': self.id, 'email': self.email}, expires_in=3600)

    def to_json(self):
        return OrderedDict({
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'email': self.email,
            'is_active': self.is_active,
            'is_superuser': self.is_superuser,
            'role': self.get_role_display(),
            'groups': [group.name for group in self.groups.all()],
            'wechat': self.wechat,
            'phone': self.phone,
            'comment': self.comment,
            'date_expired': self.date_expired.strftime('%Y-%m-%d %H:%M:%S') if self.date_expired is not None else None
        })

    @classmethod
    def create_app_user(cls, name, comment):
        from . import AccessKey
        domain_name = settings.CONFIG.DOMAIN_NAME or 'jumpserver.org'
        app = cls.objects.create(username=name, name=name, email='%s@%s' % (name, domain_name), is_active=False,
                                 role='App', enable_otp=False, comment=comment, is_first_login=False,
                                 created_by='System')
        access_key = AccessKey.objects.create(user=app)
        return app, access_key

    @classmethod
    def validate_reset_token(cls, token):
        try:
            data = signer.unsign_t(token)
            user_id = data.get('reset', None)
            user_email = data.get('email', '')
            user = cls.objects.get(id=user_id, email=user_email)

        except (signing.BadSignature, cls.DoesNotExist):
            user = None
        return user

    def reset_password(self, new_password):
        self.set_password(new_password)
        self.save()

    def delete(self):
        if self.pk == 1 or self.username == 'admin':
            return
        return super(User, self).delete()

    class Meta:
        ordering = ['username']

    #: Use this method initial user
    @classmethod
    def initial(cls):
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

        seed()
        for i in range(count):
            user = cls(username=forgery_py.internet.user_name(True),
                       email=forgery_py.internet.email_address(),
                       name=forgery_py.name.full_name(),
                       password=make_password(forgery_py.lorem_ipsum.word()),
                       role=choice(dict(User.ROLE_CHOICES).keys()),
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
