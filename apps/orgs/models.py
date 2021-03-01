import uuid
from functools import partial
from itertools import chain

from django.db import models
from django.db.models import signals
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.utils import is_uuid, lazyproperty
from common.const import choices
from common.db.models import ChoiceSet


class ROLE(ChoiceSet):
    ADMIN = choices.ADMIN, _('Organization administrator')
    AUDITOR = choices.AUDITOR, _("Organization auditor")
    USER = choices.USER, _('User')


class Organization(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_("Name"))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    members = models.ManyToManyField('users.User', related_name='orgs', through='orgs.OrganizationMember',
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
        except cls.DoesNotExist as e:
            if default:
                return cls.default()
            else:
                raise e
        return org

    def get_org_members_by_role(self, role):
        from users.models import User
        if self.is_real():
            return self.members.filter(m2m_org_members__role=role)
        users = User.objects.filter(role=role)
        return users

    @property
    def users(self):
        return self.get_org_members_by_role(ROLE.USER)

    @property
    def admins(self):
        return self.get_org_members_by_role(ROLE.ADMIN)

    @property
    def auditors(self):
        return self.get_org_members_by_role(ROLE.AUDITOR)

    def org_id(self):
        if self.is_real():
            return self.id
        elif self.is_root():
            return self.ROOT_ID
        else:
            return ''

    def get_members(self, exclude=()):
        from users.models import User
        if self.is_real():
            members = self.members.exclude(m2m_org_members__role__in=exclude)
        else:
            members = User.objects.exclude(role__in=exclude)

        return members.exclude(role=User.ROLE.APP).distinct()

    def can_admin_by(self, user):
        if user.is_superuser:
            return True
        if self.admins.filter(id=user.id).exists():
            return True
        return False

    def can_audit_by(self, user):
        if user.is_super_auditor:
            return True
        if self.auditors.filter(id=user.id).exists():
            return True
        return False

    def can_user_by(self, user):
        if self.users.filter(id=user.id).exists():
            return True
        return False

    def is_real(self):
        return self.id not in (self.DEFAULT_NAME, self.ROOT_ID, self.SYSTEM_ID)

    @classmethod
    def get_user_orgs_by_role(cls, user, role):
        if not isinstance(role, (tuple, list)):
            role = (role, )

        return cls.objects.filter(
            m2m_org_members__role__in=role,
            m2m_org_members__user_id=user.id
        ).distinct()

    @classmethod
    def get_user_all_orgs(cls, user):
        return [
            *cls.objects.filter(members=user).distinct(),
            cls.default()
        ]

    @classmethod
    def get_user_admin_orgs(cls, user):
        if user.is_anonymous:
            return cls.objects.none()
        if user.is_superuser:
            return [*cls.objects.all(), cls.default()]
        return cls.get_user_orgs_by_role(user, ROLE.ADMIN)

    @classmethod
    def get_user_user_orgs(cls, user):
        if user.is_anonymous:
            return cls.objects.none()
        return [
            *cls.get_user_orgs_by_role(user, ROLE.USER),
            cls.default()
        ]

    @classmethod
    def get_user_audit_orgs(cls, user):
        if user.is_anonymous:
            return cls.objects.none()
        if user.is_super_auditor:
            return [*cls.objects.all(), cls.default()]
        return cls.get_user_orgs_by_role(user, ROLE.AUDITOR)

    @classmethod
    def get_user_admin_or_audit_orgs(cls, user):
        if user.is_anonymous:
            return cls.objects.none()
        if user.is_superuser or user.is_super_auditor:
            return [*cls.objects.all(), cls.default()]
        return cls.get_user_orgs_by_role(user, (ROLE.AUDITOR, ROLE.ADMIN))

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

    @lazyproperty
    def resource_statistics_cache(self):
        from .caches import OrgResourceStatisticsCache
        return OrgResourceStatisticsCache(self)

    def get_total_resources_amount(self):
        from django.apps import apps
        from orgs.mixins.models import OrgModelMixin
        summary = {'users.Members': self.members.all().count()}
        for app_name, app_config in apps.app_configs.items():
            models_cls = app_config.get_models()
            for model in models_cls:
                if not issubclass(model, OrgModelMixin):
                    continue
                key = '{}.{}'.format(app_name, model.__name__)
                summary[key] = self.get_resource_amount(model)
        return summary

    def get_resource_amount(self, resource_model):
        from .utils import tmp_to_org
        from .mixins.models import OrgModelMixin

        if not issubclass(resource_model, OrgModelMixin):
            return 0
        with tmp_to_org(self):
            return resource_model.objects.all().count()


def _convert_to_uuid_set(users):
    rst = set()
    for user in users:
        if isinstance(user, models.Model):
            rst.add(user.id)
        elif not isinstance(user, uuid.UUID):
            rst.add(uuid.UUID(user))
    return rst


def _none2list(*args):
    return ([] if v is None else v for v in args)


def _users2pks_if_need(users, admins, auditors):
    pks = []
    for user in chain(users, admins, auditors):
        if hasattr(user, 'pk'):
            pks.append(user.pk)
        else:
            pks.append(user)
    return pks


class UserRoleMapper(dict):
    def __init__(self, container=set):
        super().__init__()
        self.users = container()
        self.admins = container()
        self.auditors = container()

        self[ROLE.USER] = self.users
        self[ROLE.ADMIN] = self.admins
        self[ROLE.AUDITOR] = self.auditors


class OrgMemeberManager(models.Manager):

    def remove_users(self, org, users):
        from users.models import User
        pk_set = []
        for user in users:
            if hasattr(user, 'pk'):
                pk_set.append(user.pk)
            else:
                pk_set.append(user)

        send = partial(signals.m2m_changed.send, sender=self.model, instance=org, reverse=False,
                       model=User, pk_set=pk_set, using=self.db)
        send(action="pre_remove")
        self.filter(org_id=org.id, user_id__in=pk_set).delete()
        send(action="post_remove")

    def remove_users_by_role(self, org, users=None, admins=None, auditors=None):
        from users.models import User

        if not any((users, admins, auditors)):
            return
        users, admins, auditors = _none2list(users, admins, auditors)

        send = partial(signals.m2m_changed.send, sender=self.model, instance=org, reverse=False,
                       model=User, pk_set=_users2pks_if_need(users, admins, auditors), using=self.db)

        send(action="pre_remove")
        self.filter(org_id=org.id).filter(
            Q(user__in=users, role=ROLE.USER) |
            Q(user__in=admins, role=ROLE.ADMIN) |
            Q(user__in=auditors, role=ROLE.AUDITOR)
        ).delete()
        send(action="post_remove")

    def add_users_by_role(self, org, users=None, admins=None, auditors=None):
        from users.models import User

        if not any((users, admins, auditors)):
            return
        users, admins, auditors = _none2list(users, admins, auditors)

        add_mapper = (
            (users, ROLE.USER),
            (admins, ROLE.ADMIN),
            (auditors, ROLE.AUDITOR)
        )

        oms_add = []
        for _users, _role in add_mapper:
            for _user in _users:
                if isinstance(_user, models.Model):
                    _user = _user.id
                oms_add.append(self.model(org_id=org.id, user_id=_user, role=_role))

        send = partial(signals.m2m_changed.send, sender=self.model, instance=org, reverse=False,
                       model=User, pk_set=_users2pks_if_need(users, admins, auditors), using=self.db)

        send(action='pre_add')
        self.bulk_create(oms_add, ignore_conflicts=True)
        send(action='post_add')

    def _get_remove_add_set(self, new_users, old_users):
        if new_users is None:
            return None, None
        new_users = _convert_to_uuid_set(new_users)
        return (old_users - new_users), (new_users - old_users)

    def set_user_roles(self, org, user, roles):
        """
        设置某个用户在某个组织里的角色
        """
        old_roles = set(self.filter(org_id=org.id, user=user).values_list('role', flat=True))
        new_roles = set(roles)

        roles_remove = old_roles - new_roles
        roles_add = new_roles - old_roles

        to_remove = UserRoleMapper()
        to_add = UserRoleMapper()

        for role in roles_remove:
            if role in to_remove:
                to_remove[role].add(user)
        for role in roles_add:
            if role in to_add:
                to_add[role].add(user)

        self.remove_users_by_role(
            org,
            to_remove.users,
            to_remove.admins,
            to_remove.auditors
        )

        self.add_users_by_role(
            org,
            to_add.users,
            to_add.admins,
            to_add.auditors
        )

    def set_users_by_role(self, org, users=None, admins=None, auditors=None):
        """
        给组织设置带角色的用户
        """

        oms = self.filter(org_id=org.id).values_list('role', 'user_id')

        old_mapper = UserRoleMapper()

        for role, user_id in oms:
            if role in old_mapper:
                old_mapper[role].add(user_id)

        users_remove, users_add = self._get_remove_add_set(users, old_mapper.users)
        admins_remove, admins_add = self._get_remove_add_set(admins, old_mapper.admins)
        auditors_remove, auditors_add = self._get_remove_add_set(auditors, old_mapper.auditors)

        self.remove_users_by_role(
            org,
            users_remove,
            admins_remove,
            auditors_remove
        )

        self.add_users_by_role(
            org,
            users_add,
            admins_add,
            auditors_add
        )


class OrganizationMember(models.Model):
    """
    注意：直接调用该 `Model.delete` `Model.objects.delete` 不会触发清理该用户的信号
    """

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    org = models.ForeignKey(Organization, related_name='m2m_org_members', on_delete=models.CASCADE, verbose_name=_('Organization'))
    user = models.ForeignKey('users.User', related_name='m2m_org_members', on_delete=models.CASCADE, verbose_name=_('User'))
    role = models.CharField(max_length=16, choices=ROLE.choices, default=ROLE.USER, verbose_name=_("Role"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))
    created_by = models.CharField(max_length=128, null=True, verbose_name=_('Created by'))

    objects = OrgMemeberManager()

    class Meta:
        unique_together = [('org', 'user', 'role')]
        db_table = 'orgs_organization_members'

    def __str__(self):
        return '{} is {}: {}'.format(self.user.name, self.org.name, self.role)
