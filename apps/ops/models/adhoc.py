# ~*~ coding: utf-8 ~*~
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger

__all__ = ["AdHoc"]

from ops.const import  AdHocModules

from orgs.mixins.models import JMSOrgBaseModel

logger = get_logger(__file__)


class AdHoc(JMSOrgBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    pattern = models.CharField(max_length=1024, verbose_name=_("Pattern"), default='all')
    module = models.CharField(max_length=128, choices=AdHocModules.choices, default=AdHocModules.shell,
                              verbose_name=_('Module'))
    args = models.CharField(max_length=8192, default='', verbose_name=_('Args'))
    creator = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)
    comment = models.CharField(max_length=1024, default='', verbose_name=_('Comment'), null=True, blank=True)

    @property
    def row_count(self):
        if len(self.args) == 0:
            return 0
        count = str(self.args).count('\n')
        return count + 1

    @property
    def size(self):
        return len(self.args)

    def __str__(self):
        return "{}: {}".format(self.module, self.args)

    class Meta:
        unique_together = [('name', 'org_id', 'creator')]
        verbose_name = _("Adhoc")
