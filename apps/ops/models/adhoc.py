# ~*~ coding: utf-8 ~*~
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db.models import JMSBaseModel
from common.utils import get_logger

__all__ = ["AdHoc"]

from orgs.mixins.models import JMSOrgBaseModel

logger = get_logger(__file__)


class AdHoc(JMSOrgBaseModel):
    class Modules(models.TextChoices):
        shell = 'shell', _('Shell')
        winshell = 'win_shell', _('Powershell')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    pattern = models.CharField(max_length=1024, verbose_name=_("Pattern"), default='all')
    module = models.CharField(max_length=128, choices=Modules.choices, default=Modules.shell,
                              verbose_name=_('Module'))
    args = models.CharField(max_length=1024, default='', verbose_name=_('Args'))
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
        verbose_name = _("AdHoc")
