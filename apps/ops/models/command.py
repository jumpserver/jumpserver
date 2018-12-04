# -*- coding: utf-8 -*-
#
import uuid
import json

from django.utils.translation import ugettext_lazy as _
from django.db import models

from ..ansible.runner import CommandRunner
from ..inventory import JMSInventory


class CommandExecution(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    pattern = models.CharField(max_length=64, default='all', verbose_name=_('Pattern'))
    hosts = models.ManyToManyField('assets.Asset')
    _matched_hosts = models.TextField(verbose_name=_("Matched hosts"), default='[]')
    run_as = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE)
    cmd = models.TextField(verbose_name=_("Command"))
    _result = models.TextField(blank=True, null=True, verbose_name=_('Result'))
    user_id = models.CharField(max_length=128, verbose_name=_("User id"))
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cmd

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
    def matched_hosts(self):
        if self._matched_hosts:
            return json.loads(self._matched_hosts)
        else:
            return []

    @matched_hosts.setter
    def matched_hosts(self, item):
        self._matched_hosts = json.dumps(item)

    def get_matched_hosts(self):
        return self.inventory.get_matched_hosts(self.pattern)

    @property
    def is_success(self):
        if 'error' in self.result:
            return False
        return True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        instance = super().save(force_insert=force_insert, force_update=force_update,
                                using=using, update_fields=update_fields)
        if self.pattern and self.hosts.count():
            matched_hosts = self.get_matched_hosts()



    def run(self):
        runner = CommandRunner(self.inventory)
        try:
            result = runner.execute(self.cmd, self.pattern)
            self.result = result.results_command
        except Exception as e:
            self.result = {"error": str(e)}
        self.save()
        return self.result
