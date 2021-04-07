from django.db import models
from django.utils.translation import ugettext_lazy as _


__all__ = ['SafeRoleBinding']


class SafeRoleBinding(models.Model):
    """ 用户-保险箱级别的角色绑定 """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    safe = models.ForeignKey('accounts.Safe', on_delete=models.PROTECT, verbose_name=_('Safe'))
    # only role:safe
    role = models.ForeignKey('rbac.Role', on_delete=models.PROTECT, verbose_name=_('Role'))

    class Meta:
        unique_together = ('user', 'role', 'safe')

    @classmethod
    def get_user_safes(cls, user):
        from accounts.models import Safe
        safes_ids = cls.objects.filter(user=user).values_list('safe_id', flat=True)
        safes_ids = set(list(safes_ids))
        if safes_ids:
            safes = Safe.objects.filter(id__in=safes_ids)
        else:
            safes = Safe.objects.none()
        return safes

    def get_role_permissions(self):
        perms = self.role.permissions.all().values_list('content_type__app_label', 'codename')
        perms = ['{}.{}'.format(perm[0], perm[1]) for perm in perms.order_by()]
        return perms
