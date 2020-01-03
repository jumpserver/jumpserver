import uuid
from django.conf import settings

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import is_uuid, lazyproperty


class Organization(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    users = models.ManyToManyField('users.User', related_name='related_user_orgs', blank=True)
    admins = models.ManyToManyField('users.User', related_name='related_admin_orgs', blank=True)
    auditors = models.ManyToManyField('users.User', related_name='related_audit_orgs', blank=True)
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    orgs = None
    CACHE_PREFIX = 'JMS_ORG_{}'
    ROOT_ID = '00000000-0000-0000-0000-000000000000'
    ROOT_NAME = 'ROOT'
    DEFAULT_ID = 'DEFAULT'
    DEFAULT_NAME = 'DEFAULT'
    SYSTEM_ID = '00000000-0000-0000-0000-000000000002'
    SYSTEM_NAME = 'SYSTEM'
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
        elif id_or_name in [cls.SYSTEM_ID, cls.SYSTEM_NAME]:
            return cls.system()

        try:
            if is_uuid(id_or_name):
                org = cls.objects.get(id=id_or_name)
            else:
                org = cls.objects.get(name=id_or_name)
            org.set_to_cache()
        except cls.DoesNotExist:
            org = cls.default() if default else None
        return org

    @lazyproperty
    def org_users(self):
        from users.models import User
        if self.is_real():
            return self.users.all()
        users = User.objects.filter(role=User.ROLE_USER)
        if self.is_default() and not settings.DEFAULT_ORG_SHOW_ALL_USERS:
            users = users.filter(related_user_orgs__isnull=True)
        return users

    def get_org_users(self):
        return self.org_users

    @lazyproperty
    def org_admins(self):
        from users.models import User
        if self.is_real():
            return self.admins.all()
        return User.objects.filter(role=User.ROLE_ADMIN)

    def get_org_admins(self):
        return self.org_admins

    def org_id(self):
        if self.is_real():
            return self.id
        elif self.is_root():
            return None
        else:
            return ''

    @lazyproperty
    def org_auditors(self):
        from users.models import User
        if self.is_real():
            return self.auditors.all()
        return User.objects.filter(role=User.ROLE_AUDITOR)

    def get_org_auditors(self):
        return self.org_auditors

    def get_org_members(self, exclude=()):
        from users.models import User
        members = User.objects.none()
        if 'Admin' not in exclude:
            members |= self.get_org_admins()
        if 'User' not in exclude:
            members |= self.get_org_users()
        if 'Auditor' not in exclude:
            members |= self.get_org_auditors()
        return members.exclude(role=User.ROLE_APP).distinct()

    def can_admin_by(self, user):
        if user.is_superuser:
            return True
        if self.get_org_admins().filter(id=user.id):
            return True
        return False

    def can_audit_by(self, user):
        if user.is_super_auditor:
            return True
        if self.get_org_auditors().filter(id=user.id):
            return True
        return False

    def can_user_by(self, user):
        if self.get_org_users().filter(id=user.id):
            return True
        return False

    def is_real(self):
        return self.id not in (self.DEFAULT_NAME, self.ROOT_ID, self.SYSTEM_ID)

    @classmethod
    def get_user_admin_orgs(cls, user):
        admin_orgs = []
        if user.is_anonymous:
            return admin_orgs
        elif user.is_superuser:
            admin_orgs = list(cls.objects.all())
            admin_orgs.append(cls.default())
        elif user.is_org_admin:
            admin_orgs = user.related_admin_orgs.all()
        return admin_orgs

    @classmethod
    def get_user_user_orgs(cls, user):
        user_orgs = []
        if user.is_anonymous:
            return user_orgs
        user_orgs = user.related_user_orgs.all()
        return user_orgs

    @classmethod
    def get_user_audit_orgs(cls, user):
        audit_orgs = []
        if user.is_anonymous:
            return audit_orgs
        elif user.is_super_auditor:
            audit_orgs = list(cls.objects.all())
            audit_orgs.append(cls.default())
        elif user.is_org_auditor:
            audit_orgs = user.related_audit_orgs.all()
        return audit_orgs

    @classmethod
    def get_user_admin_or_audit_orgs(self, user):
        admin_orgs = self.get_user_admin_orgs(user)
        audit_orgs = self.get_user_audit_orgs(user)
        orgs = set(admin_orgs) | set(audit_orgs)
        return orgs

    @classmethod
    def default(cls):
        return cls(id=cls.DEFAULT_ID, name=cls.DEFAULT_NAME)

    @classmethod
    def root(cls):
        return cls(id=cls.ROOT_ID, name=cls.ROOT_NAME)

    @classmethod
    def system(cls):
        return cls(id=cls.SYSTEM_ID, name=cls.SYSTEM_NAME)

    def is_root(self):
        return self.id is self.ROOT_ID

    def is_default(self):
        return self.id is self.DEFAULT_ID

    def is_system(self):
        return self.id is self.SYSTEM_ID

    def change_to(self):
        from .utils import set_current_org
        set_current_org(self)
