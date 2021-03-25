from django.db import models
from django.utils.translation import ugettext_lazy as _


__all__ = ['SystemRoleBinding', 'OrgRoleBinding', 'SafeRoleBinding']


class SystemRoleBinding(models.Model):
    """ 用户-系统角色绑定 """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    # only system-role
    role = models.ForeignKey('rbac.Role', on_delete=models.PROTECT, verbose_name=_('Role'))

    class Meta:
        unique_together = ('user', 'role')


class OrgRoleBinding(models.Model):
    """ 用户-组织角色绑定 """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    # only org-role
    role = models.ForeignKey('rbac.Role', on_delete=models.PROTECT, verbose_name=_('Role'))
    org = models.ForeignKey(
        'orgs.Organization', on_delete=models.PROTECT, verbose_name=_('Organization')
    )

    class Meta:
        unique_together = ('user', 'role', 'org')


class SafeRoleBinding(models.Model):
    """ 用户-Safe(保险箱)角色绑定 """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    role = models.ForeignKey('rbac.Role', on_delete=models.PROTECT, verbose_name=_('Role'))
    # only safe-role
    safe = models.ForeignKey('accounts.Safe', on_delete=models.PROTECT, verbose_name=_('Safe'))

    class Meta:
        unique_together = ('user', 'role', 'safe')
