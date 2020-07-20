import uuid

from django.db import models
from django.db.models import F
from django.utils.translation import ugettext_lazy as _

from common.utils import is_uuid, lazyproperty


class Organization(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))
    members = models.ManyToManyField('users.User', related_name='orgs', through='orgs.OrganizationMembers',
                                     through_fields=('org', 'user'))

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
    def members_with_role(self):
        from users.models import User
        return list(self.members.annotate(org_role=F('orgs_through__role')))

    @property
    def admins(self):
        return [member for member in self.members_with_role
                if member.org_role == OrganizationMembers.ROLE_ADMIN]

    @property
    def auditors(self):
        return [member for member in self.members_with_role
                if member.org_role == OrganizationMembers.ROLE_AUDITOR]

    @property
    def users(self):
        return [member for member in self.members_with_role
                if member.org_role == OrganizationMembers.ROLE_USER]

    # @lazyproperty
    # lazyproperty 导致用户列表中角色显示出现不稳定的情况, 如果不加会导致数据库操作次数太多
    def org_users(self):
        from users.models import User
        if self.is_real():
            return self.members.filter(orgs_through__role=OrganizationMembers.ROLE_USER)
        users = User.objects.filter(role=User.ROLE_USER)
        return users

    def get_org_users(self):
        return self.org_users()

    # @lazyproperty
    def org_admins(self):
        from users.models import User
        if self.is_real():
            return self.members.filter(orgs_through__role=OrganizationMembers.ROLE_ADMIN)
        return User.objects.filter(role=User.ROLE_ADMIN)

    def get_org_admins(self):
        return self.org_admins()

    def org_id(self):
        if self.is_real():
            return self.id
        elif self.is_root():
            return self.ROOT_ID
        else:
            return ''

    # @lazyproperty
    def org_auditors(self):
        from users.models import User
        if self.is_real():
            return self.members.filter(orgs_through__role=OrganizationMembers.ROLE_AUDITOR)
        return User.objects.filter(role=User.ROLE_AUDITOR)

    def get_org_auditors(self):
        return self.org_auditors()

    def get_org_members(self, exclude=()):
        from users.models import User
        if self.is_real():
            members = self.members.exclude(orgs_through__role__in=exclude)
        else:
            members = User.objects.exclude(role__in=exclude)

        return members.exclude(role=User.ROLE_APP).distinct()

    def can_admin_by(self, user):
        if user.is_superuser:
            return True
        if self.get_org_admins().filter(id=user.id).exists():
            return True
        return False

    def can_audit_by(self, user):
        if user.is_super_auditor:
            return True
        if self.get_org_auditors().filter(id=user.id).exists():
            return True
        return False

    def can_user_by(self, user):
        if self.get_org_users().filter(id=user.id).exists():
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
            admin_orgs.extend(cls.objects.all())
        else:
            admin_orgs.extend(cls.objects.filter(
                members_through__role=OrganizationMembers.ROLE_ADMIN,
                members_through__user_id=user.id
            ).distinct())
        admin_orgs.append(cls.default())
        return admin_orgs

    @classmethod
    def get_user_user_orgs(cls, user):
        user_orgs = []
        if user.is_anonymous:
            return user_orgs

        user_orgs.extend(cls.objects.filter(
            members_through__role=OrganizationMembers.ROLE_USER,
            members_through__user_id=user.id
        ).distinct())

        return user_orgs

    @classmethod
    def get_user_audit_orgs(cls, user):
        audit_orgs = []
        if user.is_anonymous:
            return audit_orgs
        elif user.is_super_auditor:
            audit_orgs = list(cls.objects.all())
            audit_orgs.append(cls.default())
        else:
            audit_orgs.extend(cls.objects.filter(
                members_through__role=OrganizationMembers.ROLE_AUDITOR,
                members_through__user_id=user.id
            ).distinct())
        return audit_orgs

    @classmethod
    def get_user_admin_or_audit_orgs(cls, user):
        orgs = []
        if user.is_anonymous:
            return orgs
        elif user.is_superuser:
            orgs.extend(cls.objects.all())
        else:
            orgs.extend(cls.objects.filter(
                members_through__role__id=(
                    OrganizationMembers.ROLE_AUDITOR, OrganizationMembers.ROLE_ADMIN
                ),
                members_through__user_id=user.id
            ).distinct())
        orgs.append(cls.default())
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

    @classmethod
    def all_orgs(cls):
        orgs = list(cls.objects.all())
        orgs.append(cls.default())
        return orgs


class OrganizationMembers(models.Model):
    ROLE_ADMIN = 'Admin'
    ROLE_USER = 'User'
    ROLE_AUDITOR = 'Auditor'

    ROLE_CHOICES = (
        (ROLE_ADMIN, _('Administrator')),
        (ROLE_USER, _('User')),
        (ROLE_AUDITOR, _("Auditor"))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    org = models.ForeignKey(Organization, related_name='members_through', on_delete=models.CASCADE, verbose_name=_('Organization'))
    user = models.ForeignKey('users.User', related_name='orgs_through', on_delete=models.CASCADE, verbose_name=_('User'))
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_USER, verbose_name=_("Role"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    class Meta:
        unique_together = [('org', 'user', 'role')]
        db_table = 'orgs_organization_members'

    def __str__(self):
        return '{} is {}: {}'.format(self.user.name, self.org.name, self.role)
