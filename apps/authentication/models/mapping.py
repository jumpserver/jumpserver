from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['AuthRoleBinding', 'AuthUserGroupBinding']


class AuthUserGroupBinding(JMSBaseModel):
    source = models.CharField(max_length=30, verbose_name=_('Source'))
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='auth_user_group_bindings', verbose_name=_('User')
    )
    user_group = models.ForeignKey(
        'users.UserGroup', on_delete=models.CASCADE,
        related_name='auth_user_bindings', verbose_name=_('User group')
    )
    owned = models.BooleanField(default=False, verbose_name=_('Owned'))

    class Meta:
        default_permissions = []
        constraints = [
            models.UniqueConstraint(
                fields=('source', 'user', 'user_group'),
                name='uniq_auth_user_group_source',
            )
        ]


class AuthRoleBinding(JMSBaseModel):
    source = models.CharField(max_length=30, verbose_name=_('Source'))
    role_binding = models.ForeignKey(
        'rbac.RoleBinding', on_delete=models.CASCADE,
        related_name='auth_source_bindings', verbose_name=_('Role binding')
    )
    owned = models.BooleanField(default=False, verbose_name=_('Owned'))

    class Meta:
        default_permissions = []
        constraints = [
            models.UniqueConstraint(
                fields=('source', 'role_binding'),
                name='uniq_auth_role_binding_source',
            )
        ]
