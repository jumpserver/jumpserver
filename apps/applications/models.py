from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from orgs.mixins.models import OrgModelMixin


class Application(JMSBaseModel, OrgModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    category = models.CharField(
        max_length=16, verbose_name=_('Category')
    )
    type = models.CharField(
        max_length=16, verbose_name=_('Type')
    )
    attrs = models.JSONField(default=dict, verbose_name=_('Attrs'))

    class Meta:
        verbose_name = _('Application')
        unique_together = [('org_id', 'name')]
        ordering = ('name',)
        permissions = [
            ('match_application', _('Can match application')),
        ]
