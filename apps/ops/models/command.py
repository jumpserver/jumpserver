# -*- coding: utf-8 -*-
#
import uuid
import json

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.db import models


from orgs.models import Organization
from ..ansible.runner import CommandRunner
from ..inventory import JMSInventory


class CommandExecution(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    hosts = models.ManyToManyField('assets.Asset')
    run_as = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE)
    command = models.TextField(verbose_name=_("Command"))
    _result = models.TextField(blank=True, null=True, verbose_name=_('Result'))
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True)
    is_finished = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_start = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)

    def __str__(self):
        return self.command[:10]

    @property
    def inventory(self):
        return JMSInventory(self.hosts.all(), run_as=self.run_as.username)

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

    def get_hosts_names(self):
        return ','.join(self.hosts.all().values_list('hostname', flat=True))

    def run(self):
        print('-'*10 + ' ' + ugettext('Task start') + ' ' + '-'*10)
        org = Organization.get_instance(self.run_as.org_id)
        org.change_to()
        self.date_start = timezone.now()
        ok, msg = self.run_as.is_command_can_run(self.command)
        if ok:
            runner = CommandRunner(self.inventory)
            try:
                result = runner.execute(self.command, 'all')
                self.result = result.results_command
            except Exception as e:
                print("Error occur: {}".format(e))
                self.result = {"error": str(e)}
        else:
            msg = _("Command `{}` is forbidden ........").format(self.command)
            print('\033[31m' + msg + '\033[0m')
            self.result = {"error":  msg}
        self.is_finished = True
        self.date_finished = timezone.now()
        self.save()
        print('-'*10 + ' ' + ugettext('Task end') + ' ' + '-'*10)
        return self.result
