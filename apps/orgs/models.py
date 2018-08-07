import uuid

from django.db import models
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _


class Organization(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    users = models.ManyToManyField('users.User', related_name='orgs', blank=True)
    admins = models.ManyToManyField('users.User', related_name='admin_orgs', blank=True)
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    CACHE_PREFIX = 'JMS_ORG_{}'
    ROOT_ID = 'ROOT'
    DEFAULT_ID = 'DEFAULT'

    def __str__(self):
        return self.name

    def set_to_cache(self):
        key = self.CACHE_PREFIX.format(self.id)
        cache.set(key, self, 3600)

    def expire_cache(self):
        key = self.CACHE_PREFIX.format(self.id)
        cache.set(key, self, 0)

    @classmethod
    def get_instance_from_cache(cls, oid):
        key = cls.CACHE_PREFIX.format(oid)
        return cache.get(key, None)

    @classmethod
    def get_instance(cls, oid, default=True):
        cached = cls.get_instance_from_cache(oid)
        if cached:
            return cached

        if oid == cls.DEFAULT_ID:
            return cls.default()
        elif oid == cls.ROOT_ID:
            return cls.root()

        try:
            org = cls.objects.get(id=oid)
            org.set_to_cache()
        except cls.DoesNotExist:
            org = cls.default() if default else None
        return org

    def get_org_users(self):
        from users.models import User
        if self.is_default():
            users = User.objects.filter(orgs__isnull=True)
        else:
            users = self.users.all()
        users = users.exclude(role=User.ROLE_APP)
        return users

    def get_org_admins(self):
        if self.is_real():
            return self.admins.all()
        return []

    def can_admin_by(self, user):
        if user.is_superuser:
            return True
        if user in list(self.get_org_admins()):
            return True
        return False

    def is_real(self):
        return len(str(self.id)) == 36

    @classmethod
    def get_user_admin_orgs(cls, user):
        admin_orgs = []
        if user.is_anonymous:
            return admin_orgs
        elif user.is_superuser:
            admin_orgs = list(cls.objects.all())
            admin_orgs.append(cls.default())
        elif user.is_org_admin:
            admin_orgs = user.admin_orgs.all()
        return admin_orgs

    @classmethod
    def default(cls):
        return cls(id=cls.DEFAULT_ID, name="Default")

    @classmethod
    def root(cls):
        return cls(id=cls.ROOT_ID, name='Root')

    def is_default(self):
        if self.id is self.DEFAULT_ID:
            return True
        else:
            return False
