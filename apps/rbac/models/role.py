from django.utils.translation import ugettext_lazy as _
from django.db import models

from common.db.models import JMSModel
from common.utils import lazyproperty
from .permission import Permission
from .. import const
from ..const import Scope

__all__ = ['Role']


class Role(JMSModel):
    """ 定义 角色 ｜ 角色-权限 关系 """
    Scope = const.Scope

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    scope = models.CharField(
        max_length=128, choices=Scope.choices, default=Scope.system, verbose_name=_('Scope')
    )
    users = models.ManyToManyField(
        'users.User', verbose_name=_("Users"), related_name='roles',
        through='rbac.RoleBinding', through_fields=['role', 'user'],
    )
    permissions = models.ManyToManyField(
        'rbac.Permission', related_name='roles', blank=True, verbose_name=_('Permissions')
    )
    builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    system_admin_name = 'SystemAdmin'
    org_admin_name = 'OrgAdmin'
    system_auditor_name = 'SystemAuditor'
    org_auditor_name = 'OrgAuditor'
    org_user_name = 'OrgUser'
    app_name = 'App'

    class Meta:
        unique_together = [('name', 'scope')]
        verbose_name = _('Role')

    def __str__(self):
        return '%s(%s)' % (self.name, self.get_scope_display())

    def get_permissions(self):
        admin_names = [self.system_admin_name, self.org_admin_name]

        if self.builtin and self.name in admin_names:
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
        roles = [
            (cls.system_admin_name, Scope.system, []),
            (cls.system_auditor_name, Scope.system, const.auditor_permissions),
            (cls.app_name, Scope.system, const.app_permissions),
            (cls.org_admin_name, Scope.org, []),
            (cls.org_auditor_name, Scope.org, const.auditor_permissions),
            (cls.org_user_name, Scope.org, []),
        ]
        for name, scope, permissions_define in roles:
            permissions = Permission.get_permissions(scope)
            q = Permission.get_define_permissions_q(permissions_define)
            permissions = permissions.filter(q)

            defaults = {'scope': scope, 'builtin': True, 'name': name}
            role, created = cls.objects.update_or_create(defaults, name=name)
            role.permissions.set(permissions)
