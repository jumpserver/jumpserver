from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins import CommonModelMixin
from orgs.mixins.models import OrgModelMixin


class Namespace(CommonModelMixin, OrgModelMixin):
    name = models.CharField(max_length=2048, verbose_name=_('Name'))
    comment = models.TextField(verbose_name=_('Comment'))

    class Meta:
        unique_together = [('name', 'org_id')]
