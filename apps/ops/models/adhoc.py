# ~*~ coding: utf-8 ~*~
import os.path

from django.db import models
from django.utils.translation import ugettext_lazy as _

<<<<<<< HEAD
from common.utils import get_logger
from .base import BaseAnsibleTask, BaseAnsibleExecution
from ..ansible import AdHocRunner
=======
from common.utils import get_logger, lazyproperty, make_dirs
from common.utils.translate import translate_value
from common.db.fields import (
    JsonListTextField, JsonDictCharField, EncryptJsonDictCharField,
    JsonDictTextField,
)
from orgs.mixins.models import OrgModelMixin
from ..ansible import AdHocRunner, AnsibleError
from ..inventory import JMSInventory
from ..mixin import PeriodTaskModelMixin
>>>>>>> origin

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

<<<<<<< HEAD
        runner = AdHocRunner(
            self.inventory_path, self.task.module, module_args=self.task.args,
            pattern=self.task.pattern, project_dir=self.private_dir
=======
    @property
    def adhoc_short_id(self):
        return str(self.adhoc_id).split('-')[-1]

    @property
    def log_path(self):
        dt = datetime.datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(settings.PROJECT_DIR, 'data', 'ansible', dt)
        if not os.path.exists(log_dir):
            make_dirs(log_dir)
        return os.path.join(log_dir, str(self.id) + '.log')

    def start_runner(self):
        runner = AdHocRunner(self.adhoc.inventory, options=self.adhoc.options)
        try:
            result = runner.run(
                self.adhoc.tasks,
                self.adhoc.pattern,
                self.task.name,
                execution_id=self.id
            )
            return result.results_raw, result.results_summary
        except AnsibleError as e:
            logger.warn("Failed run adhoc {}, {}".format(self.task.name, e))
            return {}, {}

    def start(self):
        self.task.latest_execution = self
        self.task.save()
        time_start = time.time()
        summary = {}
        raw = ''

        try:
            raw, summary = self.start_runner()
        except Exception as e:
            logger.error(e, exc_info=True)
            raw = {"dark": {"all": str(e)}, "contacted": []}
        finally:
            self.clean_up(summary, time_start)
            return raw, summary

    def clean_up(self, summary, time_start):
        is_success = summary.get('success', False)
        task = Task.objects.get(id=self.task_id)
        task.total_run_amount = models.F('total_run_amount') + 1
        if is_success:
            task.success_run_amount = models.F('success_run_amount') + 1
        task.save()
        AdHocExecution.objects.filter(id=self.id).update(
            is_finished=True,
            is_success=is_success,
            date_finished=timezone.now(),
            timedelta=time.time() - time_start,
            summary=summary
>>>>>>> origin
        )
        return runner

    def task_display(self):
        return str(self.task)

    class Meta:
        db_table = "ops_adhoc_execution"
        get_latest_by = 'date_start'
        verbose_name = _("AdHoc execution")
