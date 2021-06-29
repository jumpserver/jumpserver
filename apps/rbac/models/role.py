from django.utils.translation import ugettext_lazy as _
from django.db import models
from common.db.models import JMSModel


class RoleTypeChoices(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')


class Role(JMSModel):
    name = models.CharField(max_length=256, unique=True, verbose_name=_('Name'))
    type = models.CharField(
        max_length=128, choices=RoleTypeChoices.choices, default=RoleTypeChoices.system,
        verbose_name=_('Type')
    )
    permissions = models.ManyToManyField()
    builtin = models.BooleanField(default=False)
    comment = models.TextField(max_length=128, default='', blank=True, verbose_name=_('Comment'))

