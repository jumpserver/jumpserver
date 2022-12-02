# ~*~ coding: utf-8 ~*~
import os.path
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.db.models import BaseCreateUpdateModel
from common.utils import get_logger
from .base import BaseAnsibleJob, BaseAnsibleExecution
from ..ansible import AdHocRunner

__all__ = ["AdHoc", "AdHocExecution"]

logger = get_logger(__file__)


class AdHoc(BaseCreateUpdateModel):
    class Modules(models.TextChoices):
        shell = 'shell', _('Shell')
        winshell = 'win_shell', _('Powershell')

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    pattern = models.CharField(max_length=1024, verbose_name=_("Pattern"), default='all')
    module = models.CharField(max_length=128, choices=Modules.choices, default=Modules.shell,
                              verbose_name=_('Module'))
    args = models.CharField(max_length=1024, default='', verbose_name=_('Args'))
    owner = models.ForeignKey('users.User', verbose_name=_("Creator"), on_delete=models.SET_NULL, null=True)

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


class AdHocExecution(BaseAnsibleExecution):
    """
    AdHoc running history.
    """
    task = models.ForeignKey('AdHoc', verbose_name=_("Adhoc"), related_name='executions', on_delete=models.CASCADE)

    def get_runner(self):
        inv = self.task.inventory
        inv.write_to_file(self.inventory_path)

        runner = AdHocRunner(
            self.inventory_path, self.task.module, module_args=self.task.args,
            pattern=self.task.pattern, project_dir=self.private_dir
        )
        return runner

    def task_display(self):
        return str(self.task)

    class Meta:
        db_table = "ops_adhoc_execution"
        get_latest_by = 'date_start'
        verbose_name = _("AdHoc execution")
