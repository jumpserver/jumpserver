from django.utils.translation import ugettext_lazy as _, gettext
from django.db import models

from common.db.models import JMSModel
from common.utils import lazyproperty
from .permission import Permission
from ..builtin import BuiltinRole
from .. import const

__all__ = ['Role']


class Role(JMSModel):
    """ 定义 角色 ｜ 角色-权限 关系 """
    Scope = const.Scope

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    scope = models.CharField(
        max_length=128, choices=Scope.choices, default=Scope.system, verbose_name=_('Scope')
    )
    permissions = models.ManyToManyField(
        'rbac.Permission', related_name='roles', blank=True, verbose_name=_('Permissions')
    )
    builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    BuiltinRole = BuiltinRole

    class Meta:
        unique_together = [('name', 'scope')]
        verbose_name = _('Role')

    def __str__(self):
        return '%s(%s)' % (self.name, self.get_scope_display())

    def is_admin(self):
        admin_names = [self.BuiltinRole.org_admin.name, self.BuiltinRole.system_admin.name]
        yes = self.builtin and self.name in admin_names
        return yes

    @staticmethod
    def get_scope_roles_permissions(roles, scope):
        has_admin = any([r.is_admin() for r in roles])
        if has_admin:
            perms = Permission.objects.all()
        else:
            perms = Permission.objects.filter(roles=roles).distinct()
        perms = Permission.clean_permissions(perms, scope=scope)
        return perms

    @classmethod
    def get_roles_permissions(cls, roles):
        org_roles = [role for role in roles if role.scope == cls.Scope.org]
        has_org_admin = any([r.is_org_admin() for r in org_roles])
        if has_org_admin:
            org_perms = Permission.objects.all()
        else:
            org_perms = Permission.objects.filter(roles=org_roles).distinct()
        org_perms = Permission.clean_permissions(org_perms, scope=cls.Scope.org)

        system_roles = [role for role in roles if role.scope == cls.Scope.system]
        has_system_admin = any([r.is_system_admin() for r in system_roles])
        if has_system_admin:
            system_perms = Permission.objects.all()
        else:
            system_perms = Permission.objects.filter(rols=system_roles).distinct()
        system_perms = Permission.clean_permissions(system_perms, scope=cls.Scope.system)

        return

    def get_permissions(self):
        if self.is_sys_admin() or self.is_org_admin():
            permissions = Permission.objects.all()
        else:
            permissions = self.permissions.all()
        permissions = Permission.clean_permissions(permissions, self.scope)
        return permissions

    @lazyproperty
    def users_amount(self):
        return self.users.count()

    @lazyproperty
    def permissions_amount(self):
        return self.permissions.count()

    @classmethod
    def get_builtin_role(cls, name, scope):
        return cls.objects.filter(name=name, scope=scope, builtin=True).first()

    @classmethod
    def create_builtin_roles(cls):
        BuiltinRole.sync_to_db()

    @property
    def name_display(self):
        if not self.builtin:
            return self.name
        return gettext(self.name)
