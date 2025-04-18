from collections import defaultdict

from django.conf import settings
from django.core.cache import cache
from django.db import models

from common.utils import (
    get_logger,
    lazyproperty,
    bulk_create_with_signal,
)
from orgs.utils import current_org
from rbac.const import Scope
from rbac.models import RoleBinding
from users.signals import post_user_leave_org, pre_user_leave_org

logger = get_logger(__file__)


class RoleManager(models.Manager):
    scope = None
    _cache = None

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    @lazyproperty
    def role_binding_cls(self):
        from rbac.models import SystemRoleBinding, OrgRoleBinding

        if self.scope == Scope.org:
            return OrgRoleBinding
        else:
            return SystemRoleBinding

    @lazyproperty
    def role_cls(self):
        from rbac.models import SystemRole, OrgRole

        if self.scope == Scope.org:
            return OrgRole
        else:
            return SystemRole

    @property
    def display(self):
        roles = sorted(list(self.all()), key=lambda r: r.scope)
        roles_display = [role.display_name for role in roles]
        return ", ".join(roles_display)

    @property
    def role_bindings(self):
        queryset = self.role_binding_cls.objects.filter(user=self.user)
        if self.scope:
            queryset = queryset.filter(scope=self.scope)
        return queryset

    def _get_queryset(self):
        queryset = self.role_binding_cls.get_user_roles(self.user)
        if self.scope:
            queryset = queryset.filter(scope=self.scope)
        return queryset

    def get_queryset(self):
        if self._cache is not None:
            return self._cache
        return self._get_queryset()

    def clear(self):
        if not self.scope:
            return
        return self.role_bindings.delete()

    def _clean_roles(self, roles_or_ids):
        if not roles_or_ids:
            return
        is_model = isinstance(roles_or_ids[0], models.Model)
        if not is_model:
            roles = self.role_cls.objects.filter(id__in=roles_or_ids)
        else:
            roles = roles_or_ids
        roles = list([r for r in roles if r.scope == self.scope])
        return roles

    def add(self, *roles):
        if not roles:
            return

        roles = self._clean_roles(roles)
        old_ids = self.role_bindings.values_list("role", flat=True)
        need_adds = [r for r in roles if r.id not in old_ids]

        items = []
        for role in need_adds:
            kwargs = {"role": role, "user": self.user, "scope": self.scope}
            if self.scope == Scope.org:
                if current_org.is_root():
                    continue
                else:
                    kwargs["org_id"] = current_org.id
            items.append(self.role_binding_cls(**kwargs))

        try:
            result = bulk_create_with_signal(
                self.role_binding_cls, items, ignore_conflicts=True
            )
            self.user.expire_users_rbac_perms_cache()
            return result
        except Exception as e:
            logger.error("\tCreate role binding error: {}".format(e))

    def set(self, roles, clear=False):
        if clear:
            self.clear()
            self.add(*roles)
            return

        role_ids = set([r.id for r in roles])
        old_ids = self.role_bindings.values_list("role", flat=True)
        old_ids = set(old_ids)

        del_ids = old_ids - role_ids
        add_ids = role_ids - old_ids
        self.remove(*del_ids)
        self.add(*add_ids)
        self.user.save(update_fields=['date_updated'])

    def remove(self, *roles):
        if not roles:
            return
        roles = self._clean_roles(roles)
        deleted = self.role_bindings.filter(role__in=roles).delete()
        self.user.expire_users_rbac_perms_cache()
        return deleted

    def cache_set(self, roles):
        query = self._get_queryset()
        query._result_cache = roles
        self._cache = query

    @property
    def builtin_role(self):
        from rbac.builtin import BuiltinRole

        return BuiltinRole


class OrgRoleManager(RoleManager):
    def __init__(self, *args, **kwargs):
        from rbac.const import Scope

        self.scope = Scope.org
        super().__init__(*args, **kwargs)


class SystemRoleManager(RoleManager):
    def __init__(self, *args, **kwargs):
        from rbac.const import Scope

        self.scope = Scope.system
        super().__init__(*args, **kwargs)

    def remove_role_system_admin(self):
        role = self.builtin_role.system_admin.get_role()
        return self.remove(role)

    def add_role_system_admin(self):
        role = self.builtin_role.system_admin.get_role()
        return self.add(role)

    def add_role_system_user(self):
        role = self.builtin_role.system_user.get_role()
        return self.add(role)

    def add_role_system_component(self):
        role = self.builtin_role.system_component.get_role()
        self.add(role)


class RoleMixin:
    objects: models.Manager
    is_authenticated: bool
    is_valid: bool
    id: str
    source: str
    _org_roles = None
    _system_roles = None
    PERM_CACHE_KEY = "USER_PERMS_ROLES_{}_{}"
    PERM_ORG_KEY = "USER_PERMS_ORG_{}"
    _is_superuser = None
    _update_superuser = False

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
    def console_orgs(self):
        return self.cached_orgs.get("console_orgs", [])

    @lazyproperty
    def audit_orgs(self):
        return self.cached_orgs.get("audit_orgs", [])

    @lazyproperty
    def workbench_orgs(self):
        return self.cached_orgs.get("workbench_orgs", [])

    @lazyproperty
    def joined_orgs(self):
        from rbac.models import RoleBinding

        return RoleBinding.get_user_joined_orgs(self)

    @lazyproperty
    def cached_orgs(self):
        from rbac.models import RoleBinding

        key = self.PERM_ORG_KEY.format(self.id)
        data = cache.get(key)
        if data:
            return data
        console_orgs = RoleBinding.get_user_has_the_perm_orgs("rbac.view_console", self)
        audit_orgs = RoleBinding.get_user_has_the_perm_orgs("rbac.view_audit", self)
        workbench_orgs = RoleBinding.get_user_has_the_perm_orgs(
            "rbac.view_workbench", self
        )

        if settings.LIMIT_SUPER_PRIV:
            audit_orgs = list(set(audit_orgs) - set(console_orgs))

        data = {
            "console_orgs": console_orgs,
            "audit_orgs": audit_orgs,
            "workbench_orgs": workbench_orgs,
        }
        cache.set(key, data, 60 * 60)
        return data

    @lazyproperty
    def cached_role_and_perms(self):
        key = self.PERM_CACHE_KEY.format(self.id, current_org.id)
        data = cache.get(key)
        if data:
            return data

        data = {
            "org_roles": self.org_roles.all(),
            "system_roles": self.system_roles.all(),
            "perms": self.get_all_permissions(),
        }
        cache.set(key, data, 60 * 60)
        return data

    @lazyproperty
    def orgs_roles(self):
        orgs_roles = defaultdict(set)
        rbs = RoleBinding.objects_raw.filter(user=self, scope="org").prefetch_related(
            "role", "org"
        )
        for rb in rbs:
            orgs_roles[rb.org_name].add(str(rb.role.display_name))
        return orgs_roles

    def expire_rbac_perms_cache(self):
        key = self.PERM_CACHE_KEY.format(self.id, "*")
        cache.delete_pattern(key)
        key = self.PERM_ORG_KEY.format(self.id)
        cache.delete(key)

    @classmethod
    def expire_users_rbac_perms_cache(cls):
        key = cls.PERM_CACHE_KEY.format("*", "*")
        cache.delete_pattern(key)
        key = cls.PERM_ORG_KEY.format("*")
        cache.delete_pattern(key)

    @lazyproperty
    def perms(self):
        return self.cached_role_and_perms["perms"]

    @property
    def is_superuser(self):
        """
        由于这里用了 cache ，所以不能改成 self.system_roles.filter().exists() 会查询的
        """
        if self._is_superuser is not None:
            return self._is_superuser

        from rbac.builtin import BuiltinRole

        ids = [str(r.id) for r in self.system_roles.all()]
        yes = BuiltinRole.system_admin.id in ids
        self._is_superuser = yes
        return yes

    @is_superuser.setter
    def is_superuser(self, value):
        self._is_superuser = value
        self._update_superuser = True
        if value:
            self.system_roles.add_role_system_admin()
        else:
            self.system_roles.remove_role_system_admin()

    @lazyproperty
    def is_org_admin(self):
        from rbac.builtin import BuiltinRole

        if self.is_superuser:
            return True
        ids = [str(r.id) for r in self.org_roles.all()]
        yes = BuiltinRole.org_admin.id in ids
        return yes

    @property
    def is_staff(self):
        return self.is_authenticated and self.is_valid

    @is_staff.setter
    def is_staff(self, value):
        pass

    service_account_email_suffix = "@local.zone"

    @classmethod
    def create_service_account(cls, name, email, comment):
        app = cls.objects.create(
            username=name,
            name=name,
            email=email,
            comment=comment,
            is_first_login=False,
            created_by="System",
            is_service_account=True,
        )
        access_key = app.create_access_key()
        return app, access_key

    def remove(self):
        if current_org.is_root():
            return
        kwargs = dict(sender=self.__class__, user=self, org=current_org)
        pre_user_leave_org.send(**kwargs)
        self.org_roles.clear()
        post_user_leave_org.send(**kwargs)

    @classmethod
    def get_super_admins(cls):
        from rbac.models import Role, RoleBinding

        system_admin = Role.BuiltinRole.system_admin.get_role()
        return RoleBinding.get_role_users(system_admin)

    @classmethod
    def get_org_admins(cls):
        from rbac.models import Role, RoleBinding

        org_admin = Role.BuiltinRole.org_admin.get_role()
        return RoleBinding.get_role_users(org_admin)

    @classmethod
    def get_super_and_org_admins(cls):
        super_admins = cls.get_super_admins()
        org_admins = cls.get_org_admins()
        admins = org_admins | super_admins
        return admins.distinct()

    @staticmethod
    def filter_not_service_account(queryset):
        return queryset.filter(is_service_account=False)

    @classmethod
    def get_nature_users(cls):
        queryset = cls.objects.all()
        return cls.filter_not_service_account(queryset)

    @classmethod
    def get_org_users(cls, org=None):
        queryset = cls.objects.all()
        if org is None:
            org = current_org
        if not org.is_root():
            queryset = org.get_members()
        queryset = cls.filter_not_service_account(queryset)
        return queryset

    def get_all_permissions(self):
        from rbac.models import RoleBinding

        perms = RoleBinding.get_user_perms(self)

        if settings.LIMIT_SUPER_PRIV and "view_console" in perms:
            perms = [p for p in perms if p != "view_audit"]
        return perms
