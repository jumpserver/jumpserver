import uuid
from django.utils.translation import ugettext_lazy as _
from django.db import models
from common.db.models import JMSModel
from ..const import RoleTypeChoices

__all__ = ['Role', 'RoleBinding']


class Role(JMSModel):
    """ 定义 角色 ｜ 角色-权限 关系 """
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    type = models.CharField(
        max_length=128, choices=RoleTypeChoices.choices, default=RoleTypeChoices.system,
        verbose_name=_('Type')
    )
    permissions = models.ManyToManyField(
        'rbac.Permission', related_name='roles', blank=True, verbose_name=_('Permissions')
    )
    builtin = models.BooleanField(default=False, verbose_name=_('Built-in'))
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))


class RoleBinding(models.Model):
    """ 定义 用户-角色 关系 """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    type = models.CharField(
        max_length=128, choices=RoleTypeChoices.choices, default=RoleTypeChoices.system,
        verbose_name=_('Type')
    )
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name=_('User'))
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name=_('Role'))
    org = models.ForeignKey(
        'orgs.Organization', null=True, on_delete=models.CASCADE, verbose_name=_('Organization')
    )
