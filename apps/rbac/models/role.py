from django.utils.translation import ugettext_lazy as _
from django.db import models

from common.db.models import JMSModel

from .permission import Permission
from rbac import const

__all__ = ['Role', 'RoleBinding']


class Scope(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


class Role(JMSModel):
    """ 定义 角色 ｜ 角色-权限 关系 """
    Scope = Scope

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    scope = models.CharField(
        max_length=128, choices=Scope.choices, default=Scope.system,
        verbose_name=_('Scope')
    )
    permissions = models.ManyToManyField(
        'rbac.Permission', related_name='roles', blank=True, verbose_name=_('Permissions')
    )
    builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    admin_name = 'SystemAdmin'
    system_admin_name = 'SystemAdmin'
    org_admin_name = 'OrgAdmin'
    auditor_name = 'Auditor'
    user_name = 'User'
    app_name = 'App'

    class Meta:
        unique_together = [('name', 'scope')]

    def get_permissions(self):
        if self.builtin and self.name in [self.system_admin_name, self.org_admin_name]:
            permissions = Permission.objects.all()
        else:
            permissions = self.permissions.all()

        excludes = const.exclude_permissions
        if self.scope == Scope.org:
            excludes.extend(const.system_scope_permissions)

        for app_label, code_name in excludes:
            permissions = permissions.exclude(codename=code_name, content_type__app_label=app_label)
        return permissions

    def get_bound_users(self):
        from users.models import User
        users_id = RoleBinding.objects.filter(role=self).values_list('user_id', flat=True)
        return User.objects.filter(id__in=users_id)

    def __str__(self):
        return '%s (%s)' % (self.name, self.get_scope_display())

    @classmethod
    def get_builtin_role(cls, name, scope):
        return cls.objects.filter(name=name, scope=scope, builtin=True).first()


class RoleBinding(JMSModel):
    """ 定义 用户-角色 关系 """
    Scope = Role.Scope

    scope = models.CharField(
        max_length=128, choices=Scope.choices, default=Scope.system,
        verbose_name=_('Scope')
    )
    user = models.ForeignKey(
        'users.User', related_name='role_bindings', on_delete=models.CASCADE, verbose_name=_('User')
    )
    role = models.ForeignKey(
        Role, related_name='role_bindings', on_delete=models.CASCADE, verbose_name=_('Role')
    )
    org = models.ForeignKey(
        'orgs.Organization', related_name='role_bindings', blank=True, null=True,
        on_delete=models.CASCADE, verbose_name=_('Organization')
    )

    class Meta:
        verbose_name = _('Role binding')
        unique_together = ('user', 'role', 'org')

    def __str__(self):
        display = '{user} & {role}'.format(user=self.user, role=self.role)
        if self.org:
            display += ' | {org}'.format(org=self.org)
        return display

    def save(self, *args, **kwargs):
        self.scope = self.role.scope
        return super().save(*args, **kwargs)
