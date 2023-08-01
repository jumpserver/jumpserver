from django.db import models
from django.utils.translation import gettext_lazy as _, gettext

from common.db.models import JMSBaseModel
from common.utils import lazyproperty
from .permission import Permission
from .. import const
from ..builtin import BuiltinRole

__all__ = ['Role', 'SystemRole', 'OrgRole']


class SystemRoleManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(scope=const.Scope.system)


class OrgRoleManager(models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(scope=const.Scope.org)


class Role(JMSBaseModel):
    """ 定义 角色 ｜ 角色-权限 关系 """
    Scope = const.Scope

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    scope = models.CharField(
        max_length=128, choices=Scope.choices, default=Scope.system, verbose_name=_('Scope')
    )
    permissions = models.ManyToManyField(
        'rbac.Permission', related_name='roles', blank=True, verbose_name=_('Permissions')
    )
    builtin = models.BooleanField(default=False, verbose_name=_('Builtin'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    BuiltinRole = BuiltinRole
    objects = models.Manager()
    org_roles = OrgRoleManager()
    system_roles = SystemRoleManager()

    class Meta:
        unique_together = [('name', 'scope')]
        verbose_name = _('Role')

    def __str__(self):
        return '%s(%s)' % (self.name, self.get_scope_display())

    def is_system_admin(self):
        return str(self.id) == self.BuiltinRole.system_admin.id and self.builtin

    def is_org_admin(self):
        return str(self.id) == self.BuiltinRole.org_admin.id and self.builtin

    def is_admin(self):
        yes = self.is_system_admin() or self.is_org_admin()
        return yes

    @staticmethod
    def get_scope_roles_perms(roles, scope):
        has_admin = any([r.is_admin() for r in roles])
        if has_admin:
            perms = Permission.objects.all()
        else:
            perms = Permission.objects.filter(roles__in=roles).distinct()
        perms = Permission.clean_permissions(perms, scope=scope)
        return perms

    @classmethod
    def get_roles_permissions(cls, roles):
        org_roles = [role for role in roles if role.scope == cls.Scope.org]
        org_perms_id = cls.get_scope_roles_perms(org_roles, cls.Scope.org) \
            .values_list('id', flat=True)

        system_roles = [role for role in roles if role.scope == cls.Scope.system]
        system_perms_id = cls.get_scope_roles_perms(system_roles, cls.Scope.system) \
            .values_list('id', flat=True)
        perms_id = set(org_perms_id) | set(system_perms_id)
        permissions = Permission.objects.filter(id__in=perms_id) \
            .prefetch_related('content_type')
        return permissions

    @classmethod
    def get_roles_perms(cls, roles):
        permissions = cls.get_roles_permissions(roles)
        return Permission.to_perms(permissions)

    def get_permissions(self):
        if self.is_admin():
            permissions = Permission.objects.all()
        else:
            permissions = self.permissions.all()
        permissions = Permission.clean_permissions(permissions, self.scope)
        return permissions

    @lazyproperty
    def users(self):
        from .rolebinding import RoleBinding
        return RoleBinding.get_role_users(self)

    @lazyproperty
    def users_amount(self):
        return self.users.count()

    @lazyproperty
    def permissions_amount(self):
        return self.permissions.count()

    @classmethod
    def create_builtin_roles(cls):
        BuiltinRole.sync_to_db()

    @property
    def display_name(self):
        if not self.builtin:
            return self.name
        return gettext(self.name)

    def is_org(self):
        return self.scope == const.Scope.org

    @classmethod
    def get_roles_by_perm(cls, perm):
        app_label, codename = perm.split('.')
        p = Permission.objects.filter(
            codename=codename,
            content_type__app_label=app_label
        ).first()
        if not p:
            return p.roles.none()
        role_ids = list(p.roles.all().values_list('id', flat=True))
        admin_ids = [BuiltinRole.system_admin.id, BuiltinRole.org_admin.id]
        role_ids += admin_ids
        return cls.objects.filter(id__in=role_ids)


class SystemRole(Role):
    objects = SystemRoleManager()

    class Meta:
        proxy = True
        verbose_name = _('System role')


class OrgRole(Role):
    objects = OrgRoleManager()

    class Meta:
        proxy = True
        verbose_name = _('Organization role')
