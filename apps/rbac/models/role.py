from django.utils.translation import ugettext_lazy as _
from django.db import models

from common.db.models import JMSModel
from orgs.utils import current_org
from .permission import Permission
from .. import const

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

    system_admin_name = 'SystemAdmin'
    org_admin_name = 'OrgAdmin'
    system_auditor_name = 'SystemAuditor'
    org_auditor_name = 'OrgAuditor'
    system_user_name = 'SystemUser'
    org_user_name = 'OrgUser'
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

    @classmethod
    def create_builtin_roles(cls):
        scope_role_names_mapper = {
            cls.Scope.system: [
                cls.system_admin_name, cls.system_auditor_name, cls.system_user_name,
                cls.app_name,
            ],
            cls.Scope.org: [cls.org_admin_name, cls.org_auditor_name, cls.org_user_name]
        }
        for scope, role_names in scope_role_names_mapper.items():
            for name in role_names:
                cls.objects.create(name=name, scope=scope, builtin=True)


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

    def get_perms(self):
        perms = list(self.role.get_permissions().values_list(
            'content_type__app_label', 'codename'
        ))
        return set(["%s.%s" % (ct, codename) for ct, codename in perms])

    @classmethod
    def get_binding_perms(cls, bindings):
        perms = set()
        for binding in bindings:
            perms |= binding.get_perms()
        return perms

    @classmethod
    def get_user_perms(cls, user):
        q = models.Q(user=user, org__isnull=True, scope=cls.Scope.system)
        if current_org and not current_org.is_root:
            q |= models.Q(user=user, org=current_org.org_id, scope=cls.Scope.org)
        bindings = cls.objects.filter(q)
        perms = cls.get_binding_perms(bindings)
        return perms

    @classmethod
    def get_user_system_roles(cls, user):
        role_ids = cls.objects.filter(user=user, org__isnull=True, scope=cls.Scope.system)\
            .values_list('role', flat=True)
        roles = Role.objects.filter(id__in=role_ids)
        return roles

    @classmethod
    def get_user_current_org_role(cls, user):
        role_ids = cls.objects.filter(user=user, org=current_org, scope=cls.Scope.org)\
            .values_list('role', flat=True)
        roles = Role.objects.filter(id__in=role_ids)
        return roles

    @classmethod
    def get_user_roles(cls, user):
        role_ids = cls.objects.filter(user=user).values_list('role', flat=True)
        roles = Role.objects.filter(id__in=role_ids)
        return roles
