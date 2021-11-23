from django.utils.translation import ugettext_lazy as _
from django.db import models

from common.db.models import JMSModel
from orgs.utils import current_org

from .role import Role
from .. const import Scope

__all__ = ['RoleBinding']


class RoleBinding(JMSModel):
    """ 定义 用户-角色 关系 """

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
        perms = sorted(list(perms), key=cls.sort_perms)
        return perms

    @staticmethod
    def sort_perms(perm):
        perm_split = perm.split('.')
        if len(perm_split) != 2:
            return perm_split
        app, code = perm_split[0], perm_split[1]
        action_resource = code.split('_')
        if len(action_resource) == 1:
            action_resource.append('')
        action = action_resource[0]
        resource = '_'.join(action_resource[1:])
        return [app, resource, action]

    @classmethod
    def get_user_perms(cls, user):
        q = models.Q(user=user, org__isnull=True, scope=Scope.system)
        if current_org and not current_org.is_root:
            q |= models.Q(user=user, org=current_org.org_id, scope=Scope.org)
        bindings = cls.objects.filter(q)
        perms = cls.get_binding_perms(bindings)
        return perms

    @classmethod
    def get_user_system_roles(cls, user):
        role_ids = cls.objects.filter(user=user, org__isnull=True, scope=Scope.system) \
            .values_list('role', flat=True)
        roles = Role.objects.filter(id__in=role_ids)
        return roles

    @classmethod
    def get_user_current_org_role(cls, user):
        role_ids = cls.objects.filter(user=user, org=current_org, scope=Scope.org) \
            .values_list('role', flat=True)
        roles = Role.objects.filter(id__in=role_ids)
        return roles

    @classmethod
    def get_user_roles(cls, user):
        role_ids = cls.objects.filter(user=user).values_list('role', flat=True)
        roles = Role.objects.filter(id__in=role_ids)
        return roles
