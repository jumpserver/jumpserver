# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser
from django.core import signing
from django.db import models, IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.shortcuts import reverse

from rest_framework.authtoken.models import Token

from common.utils import encrypt, decrypt, date_expired_default
from common.mixins import NoDeleteModelMixin


class UserGroup(NoDeleteModelMixin):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Name'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    def has_member(self, user):
        if user in self.users.all():
            return True
        return False

    def delete(self):
        if self.name != 'Default':
            self.users.clear()
            return super(UserGroup, self).delete()
        return True

    class Meta:
        db_table = 'user_group'

    @classmethod
    def initial(cls):
        group, created = cls.objects.get_or_create(name='Default', comment='Default user group for all user',
                                                   created_by='System')
        return group

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed, choice
        import forgery_py

        seed()
        for i in range(count):
            group = cls(name=forgery_py.name.full_name(),
                        comment=forgery_py.lorem_ipsum.sentence(),
                        created_by=choice(User.objects.all()).username)
            try:
                group.save()
            except IntegrityError:
                print('Error continue')
                continue


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
    _private_key = models.CharField(max_length=5000, blank=True, verbose_name=_('ssh private key'))
    _public_key = models.CharField(max_length=1000, blank=True, verbose_name=_('ssh public key'))
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
    def password_raw(self, password_raw_):
        self.set_password(password_raw_)

    def get_absolute_url(self):
        return reverse('users:user-detail', args=(self.id,))

    @property
    def is_expired(self):
        if self.date_expired > timezone.now():
            return False
        else:
            return True

    @property
    def is_valid(self):
        if self.is_active and not self.is_expired:
            return True
        return False

    @property
    def private_key(self):
        return decrypt(self._private_key)

    @private_key.setter
    def private_key(self, private_key_raw):
        self._private_key = encrypt(private_key_raw)

    @property
    def public_key(self):
        return decrypt(self._public_key)

    @public_key.setter
    def public_key(self, public_key_raw):
        self._public_key = encrypt(public_key_raw)

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

    def is_member_of(self, user_group):
        if user_group in self.groups.all():
            return True
        return False

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

    def delete(self):
        if self.pk == 1:
            return
        return super(User, self).delete()

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
