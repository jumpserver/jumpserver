# -*- coding: utf-8 -*-
#
import uuid
import json

from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.db import models

from common.utils import lazyproperty
from orgs.models import Organization
from orgs.mixins.models import OrgModelMixin
from ..ansible.runner import CommandRunner
from ..inventory import JMSInventory


class CommandExecution(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    hosts = models.ManyToManyField('assets.Asset')
    run_as = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE)
    command = models.TextField(verbose_name=_("Command"))
    _result = models.TextField(blank=True, null=True, verbose_name=_('Result'))
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'))
    date_finished = models.DateTimeField(null=True, verbose_name=_('Date finished'))

    def __str__(self):
        return self.command[:10]

    @property
    def inventory(self):
        if self.run_as.username_same_with_user:
            username = self.user.username
        else:
            username = self.run_as.username
        inv = JMSInventory(self.hosts.all(), run_as=username)
        return inv

    @lazyproperty
    def run_as_display(self):
        return str(self.run_as)

    @lazyproperty
    def user_display(self):
        return str(self.user)

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
                host = self.hosts.first()
                if host.is_windows():
                    shell = 'win_shell'
                else:
                    shell = 'shell'
                result = runner.execute(self.command, 'all', module=shell)
                self.result = result.results_command
            except SoftTimeLimitExceeded as e:
                print("Run timeout than 60s")
                self.result = {"error": str(e)}
            except Exception as e:
                print("Error occur: {}".format(e))
                self.result = {"error": str(e)}
        else:
            msg = _("Command `{}` is forbidden ........").format(self.command)
            print('\033[31m' + msg + '\033[0m')
            self.result = {"error":  msg}
        self.org_id = self.run_as.org_id
        self.is_finished = True
        self.date_finished = timezone.now()
        self.save()
        print('-'*10 + ' ' + ugettext('Task end') + ' ' + '-'*10)
        return self.result
