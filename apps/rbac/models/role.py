import uuid
from django.utils.translation import ugettext_lazy as _
from django.db import models
from common.db.models import JMSModel
from ..const import ScopeChoices

__all__ = ['Role', 'RoleBinding']


class Role(JMSModel):
    """ 定义 角色 ｜ 角色-权限 关系 """
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    scope = models.CharField(
        max_length=128, choices=ScopeChoices.choices, default=ScopeChoices.system,
        verbose_name=_('Scope')
    )
    permissions = models.ManyToManyField(
        'rbac.Permission', related_name='roles', blank=True, verbose_name=_('Permissions')
    )
    builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return '%s (%s)' % (self.name, self.get_scope_display())


class RoleBinding(models.Model):
    """ 定义 用户-角色 关系 """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    scope = models.CharField(
        max_length=128, choices=ScopeChoices.choices, default=ScopeChoices.system,
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
        return '{user} - {role} | {org}'.format(user=self.user, role=self.role, org=self.org)

    def save(self, *args, **kwargs):
        self.scope = self.role.scope
        return super().save(*args, **kwargs)
