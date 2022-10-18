# ~*~ coding: utf-8 ~*~
import os.path

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger
from .base import BaseAnsibleTask, BaseAnsibleExecution
from ..ansible import AdHocRunner

__all__ = ["AdHoc", "AdHocExecution"]


logger = get_logger(__file__)


class AdHoc(BaseAnsibleTask):
    pattern = models.CharField(max_length=1024, verbose_name=_("Pattern"), default='all')
    module = models.CharField(max_length=128, default='shell', verbose_name=_('Module'))
    args = models.CharField(max_length=1024, default='', verbose_name=_('Args'))
    last_execution = models.ForeignKey('AdHocExecution', verbose_name=_("Last execution"),
                                       on_delete=models.SET_NULL, null=True, blank=True)

    def get_register_task(self):
        from ops.tasks import run_adhoc
        return "run_adhoc_{}".format(self.id), run_adhoc, (str(self.id),), {}

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
