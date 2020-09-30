from django.utils.translation import ugettext_lazy as _

from common.db import models
from orgs.mixins.models import OrgModelMixin


class Namespace(models.JMSModel, OrgModelMixin):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    comment = models.TextField(default='', verbose_name=_('Comment'))

    class Meta:
        unique_together = [('name', 'org_id')]
