import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import is_uuid


class Organization(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    users = models.ManyToManyField('users.User', related_name='orgs', blank=True)
    admins = models.ManyToManyField('users.User', related_name='admin_orgs', blank=True)
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    orgs = None
    CACHE_PREFIX = 'JMS_ORG_{}'
    ROOT_ID = '00000000-0000-0000-0000-000000000000'
    ROOT_NAME = 'ROOT'
    DEFAULT_ID = 'DEFAULT'
    DEFAULT_NAME = 'DEFAULT'
    _user_admin_orgs = None

    class Meta:
        verbose_name = _("Organization")

    def __str__(self):
        return self.name

    def set_to_cache(self):
        if self.__class__.orgs is None:
            self.__class__.orgs = {}
        self.__class__.orgs[str(self.id)] = self

    def expire_cache(self):
        self.__class__.orgs.pop(str(self.id), None)

    @classmethod
    def get_instance_from_cache(cls, oid):
        if not cls.orgs or not isinstance(cls.orgs, dict):
            return None
        return cls.orgs.get(str(oid))

    @classmethod
    def get_instance(cls, id_or_name, default=False):
        cached = cls.get_instance_from_cache(id_or_name)
        if cached:
            return cached

        if id_or_name is None:
            return cls.default() if default else None
        elif id_or_name in [cls.DEFAULT_ID, cls.DEFAULT_NAME, '']:
            return cls.default()
        elif id_or_name in [cls.ROOT_ID, cls.ROOT_NAME]:
            return cls.root()

        try:
            if is_uuid(id_or_name):
                org = cls.objects.get(id=id_or_name)
            else:
                org = cls.objects.get(name=id_or_name)
            org.set_to_cache()
        except cls.DoesNotExist:
            org = cls.default() if default else None
        return org

    def get_org_users(self, include_app=False):
        from users.models import User
        if self.is_real():
            users = self.users.all()
        else:
            users = User.objects.all()
        if not include_app:
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
        return self.id not in (self.DEFAULT_NAME, self.ROOT_ID)

    @classmethod
    def get_user_admin_orgs(cls, user):
        admin_orgs = []
        if user.is_anonymous:
            return admin_orgs
        elif user.is_superuser or user.is_auditor:
            admin_orgs = list(cls.objects.all())
            admin_orgs.append(cls.default())
        elif user.is_org_admin:
            admin_orgs = user.admin_orgs.all()
        return admin_orgs

    @classmethod
    def default(cls):
        return cls(id=cls.DEFAULT_ID, name=cls.DEFAULT_NAME)

    @classmethod
    def root(cls):
        return cls(id=cls.ROOT_ID, name=cls.ROOT_NAME)

    def is_root(self):
        if self.id is self.ROOT_ID:
            return True
        else:
            return False

    def is_default(self):
        if self.id is self.DEFAULT_ID:
            return True
        else:
            return False

    def change_to(self):
        from .utils import set_current_org
        set_current_org(self)
