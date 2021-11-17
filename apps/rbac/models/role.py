from django.utils.translation import ugettext_lazy as _
from django.db import models

from common.db.models import JMSModel
from common.utils import lazyproperty
from .permission import Permission
from .. import const

__all__ = ['Role']


class Scope(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


class Role(JMSModel):
    """ 定义 角色 ｜ 角色-权限 关系 """
    Scope = Scope

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

    def get_permissions(self):
        admin_names = [self.system_admin_name, self.org_admin_name]
        if self.builtin and self.name in admin_names:
            permissions = Permission.objects.all()
        else:
            permissions = self.permissions.all()

        excludes = list(const.exclude_permissions)
        if self.scope == Scope.org:
            excludes.extend(const.system_scope_permissions)

        for app_label, code_name in excludes:
            permissions = permissions.exclude(
                codename=code_name,
                content_type__app_label=app_label
            )
        return permissions

    @lazyproperty
    def users_amount(self):
        return self.users.count()

    @lazyproperty
    def permissions_amount(self):
        return self.permissions.count()

    def __str__(self):
        return '%s (%s)' % (self.name, self.get_scope_display())

    @classmethod
    def get_builtin_role(cls, name, scope):
        return cls.objects.filter(name=name, scope=scope, builtin=True).first()

    @classmethod
    def create_builtin_roles(cls):
        scope_role_names_mapper = {
            cls.Scope.system: [
                cls.system_admin_name, cls.system_auditor_name,
                cls.system_user_name, cls.app_name,
            ],
            cls.Scope.org: [
                cls.org_admin_name, cls.org_auditor_name, cls.org_user_name
            ]
        }
        for scope, role_names in scope_role_names_mapper.items():
            for name in role_names:
                cls.objects.create(name=name, scope=scope, builtin=True)

