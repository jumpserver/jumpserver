# -*- coding: utf-8 -*-
#
import uuid
import json

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.db import models

from ..ansible.runner import CommandRunner
from ..inventory import JMSInventory


class CommandExecution(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    hosts = models.ManyToManyField('assets.Asset')
    run_as = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE)
    script = models.TextField(verbose_name=_("Command"))
    _result = models.TextField(blank=True, null=True, verbose_name=_('Result'))
    user_id = models.CharField(max_length=128, verbose_name=_("User id"))
    is_finished = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_start = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)

    def __str__(self):
        return self.script[:10]

    @property
    def inventory(self):
        return JMSInventory(self.hosts.all(), run_as=self.run_as)

    @property
    def result(self):
        if self._result:
            return json.loads(self._result)
        else:
            return {}

    @result.setter
    def result(self, item):
        self._result = json.dumps(item)

    @property
    def is_success(self):
        if 'error' in self.result:
            return False
        return True

    def run(self):
        self.date_start = timezone.now()
        runner = CommandRunner(self.inventory)
        try:
            result = runner.execute(self.script, 'all')
            self.result = result.results_command
        except Exception as e:
            self.result = {"error": str(e)}
        self.is_finished = True
        self.date_finished = timezone.now()
        self.save()
        return self.result
