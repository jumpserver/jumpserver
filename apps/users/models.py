# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

import datetime

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser, Permission
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import IntegrityError
from django.utils.translation import ugettext_lazy as _
from rest_framework.authtoken.models import Token

from django.core import signing

# class Role(models.Model):
#     name = models.CharField('name', max_length=80, unique=True)
#     permissions = models.ManyToManyField(
#         Permission,
#         verbose_name='permissions',
#         blank=True,
#     )
#     date_created = models.DateTimeField(auto_now_add=True)
#     created_by = models.CharField(max_length=100)
#     comment = models.CharField(max_length=80, blank=True)
#
#     def __unicode__(self):
#         return self.name
#
#     def delete(self, using=None, keep_parents=False):
#         if self.users.all().count() > 0:
#             raise OperationalError('Role %s has some member, should not be delete.' % self.name)
#         else:
#             return super(Role, self).delete(using=using, keep_parents=keep_parents)
#
#     class Meta:
#         db_table = 'role'
#
#     @classmethod
#     def initial(cls):
#         roles = {
#             'Administrator': {'permissions': Permission.objects.all(), 'comment': '管理员'},
#             'User': {'permissions': [], 'comment': '用户'},
#             'Auditor': {'permissions': Permission.objects.filter(content_type__app_label='audits'),
#                         'comment': '审计员'},
#         }

#         for role_name, props in roles.items():
#            if not cls.objects.filter(name=role_name):
#                role = cls.objects.create(name=role_name, comment=props.get('comment', ''), created_by='System')
#                if props.get('permissions'):
#                    role.permissions = props.get('permissions')


class UserGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Name'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'user-group'

    @classmethod
    def initial(cls):
        group_or_create = cls.objects.get_or_create(name='Default', comment='Default user group for all user',
                                                    created_by='System')
        return group_or_create[0]

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, randint, choice
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            group = cls(name=forgery_py.name.full_name(),
                        comment=forgery_py.lorem_ipsum.sentence(),
                        created_by=choice(User.objects.all()).username
                    )
            try:
                group.save()
            except IntegrityError:
                print('Error continue')
                continue


def date_expired_default():
    return timezone.now() + timezone.timedelta(days=365 * 70)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('Admin', _('Administrator')),
        ('User', _('User')),
    )

    username = models.CharField(max_length=20, unique=True, verbose_name=_('Username'))
    name = models.CharField(max_length=20, blank=True, verbose_name=_('Name'))
    email = models.EmailField(max_length=30, unique=True, verbose_name=_('Email'))
    groups = models.ManyToManyField(UserGroup, related_name='users', blank=True, verbose_name=_('User group'))
    role = models.CharField(choices=ROLE_CHOICES, default='User', max_length=10, blank=True, verbose_name=_('Role'))
    avatar = models.ImageField(upload_to="avatar", verbose_name=_('Avatar'))
    wechat = models.CharField(max_length=30, blank=True, verbose_name=_('Wechat'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Phone'))
    enable_otp = models.BooleanField(default=False, verbose_name=_('Enable OTP'))
    secret_key_otp = models.CharField(max_length=16, blank=True)
    private_key = models.CharField(max_length=5000, blank=True, verbose_name=_('ssh private key'))
    public_key = models.CharField(max_length=1000, blank=True, verbose_name=_('ssh public key'))
    comment = models.TextField(max_length=200, blank=True, verbose_name=_('Comment'))
    is_first_login = models.BooleanField(default=False)
    date_expired = models.DateTimeField(default=date_expired_default, blank=True, null=True,
                                        verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=30, default='', verbose_name=_('Created by'))

    @property
    def password_raw(self):
        raise AttributeError('Password raw is not readable attribute')

    #: Use this attr to set user object password, example
    #: user = User(username='example', password_raw='password', ...)
    #: It's equal:
    #: user = User(username='example', ...)
    #: user.set_password('password')
    @password_raw.setter
    def password_raw(self, raw_password):
        self.set_password(raw_password)

    @property
    def is_expired(self):
        if self.date_expired > timezone.now():
            return False
        else:
            return True

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
    def is_staff(self):
        if self.is_authenticated and self.is_active and not self.is_expired and self.is_superuser:
            return True
        else:
            return False

    @is_staff.setter
    def is_staff(self, value):
        pass

    def save(self, *args, **kwargs):
        # If user not set name, it's default equal username
        if not self.name:
            self.name = self.username

        super(User, self).save(*args, **kwargs)
        # Set user default group 'All'
        # Todo: It's have bug
        group = UserGroup.initial()
        if group not in self.groups.all():
            self.groups.add(group)
            # super(User, self).save(*args, **kwargs)

    @property
    def private_token(self):
        return self.get_private_token()

    def get_private_token(self):
        try:
            token = Token.objects.get(user=self)
        except Token.DoesNotExist:
            token = Token.objects.create(user=self)

        return token.key

    def refresh_private_token(self):
        Token.objects.filter(user=self).delete()
        return Token.objects.create(user=self)

    def generate_reset_token(self):
        return signing.dumps({'reset': self.id, 'email': self.email})

    @classmethod
    def validate_reset_token(cls, token, max_age=3600):
        try:
            data = signing.loads(token, max_age=max_age)
            user_id = data.get('reset', None)
            user_email = data.get('email', '')
            user = cls.objects.get(id=user_id, email=user_email)

        except (signing.BadSignature, cls.DoesNotExist):
            user = None
        return user

    def reset_password(self, new_password):
        self.set_password(new_password)
        self.save()

    class Meta:
        db_table = 'user'

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
                       created_by=choice(cls.objects.all()).username,
                   )
            try:
                user.save()
            except IntegrityError:
                print('Duplicate Error, continue ...')
                continue
            user.groups.add(choice(UserGroup.objects.all()))
            user.save()


def init_all_models():
    for model in (UserGroup, User):
        if hasattr(model, 'initial'):
            model.initial()


def generate_fake():
    for model in (UserGroup, User):
        if hasattr(model, 'generate_fake'):
            model.generate_fake()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        try:
            Token.objects.create(user=instance)
        except IntegrityError:
            pass

