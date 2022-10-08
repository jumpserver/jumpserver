from django.db import models
from django.utils.translation import gettext_lazy as _

from orgs.mixins.models import JMSOrgBaseModel
from .base import BaseAnsibleExecution, BaseAnsibleTask


class PlaybookTemplate(JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    path = models.FilePathField(verbose_name=_("Path"))
    comment = models.TextField(verbose_name=_("Comment"), blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Playbook template")
        unique_together = [('org_id', 'name')]


class Playbook(BaseAnsibleTask):
    path = models.FilePathField(max_length=1024, verbose_name=_("Playbook"))
    owner = models.ForeignKey('users.User', verbose_name=_("Owner"), on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    template = models.ForeignKey('PlaybookTemplate', verbose_name=_("Template"), on_delete=models.SET_NULL, null=True)
    last_execution = models.ForeignKey('PlaybookExecution', verbose_name=_("Last execution"), on_delete=models.SET_NULL, null=True, blank=True)

    def get_register_task(self):
        name = "automation_strategy_period_{}".format(str(self.id)[:8])
        task = execute_automation_strategy.name
        args = (str(self.id), Trigger.timing)
        kwargs = {}
        return name, task, args, kwargs


class PlaybookExecution(BaseAnsibleExecution):
    task = models.ForeignKey('Playbook', verbose_name=_("Task"), on_delete=models.CASCADE)
    path = models.FilePathField(max_length=1024, verbose_name=_("Run dir"))
