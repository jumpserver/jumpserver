import uuid
from django.utils.translation import ugettext_lazy as _
from django.db import models
from common.db.models import JMSModel

__all__ = ['Role', 'RoleBinding']


class RoleTypeChoices(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


class Role(JMSModel):
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
