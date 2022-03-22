# -*- coding: utf-8 -*-
#
import uuid
import json

from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.db import models

from terminal.notifications import CommandExecutionAlert
from assets.models import Asset
from common.utils import lazyproperty
from orgs.models import Organization
from orgs.mixins.models import OrgModelMixin
from orgs.utils import tmp_to_org
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

    def save(self, *args, **kwargs):
        with tmp_to_org(self.run_as.org_id):
            super().save(*args, **kwargs)

    @property
    def inventory(self):
        if self.run_as.username_same_with_user:
            username = self.user.username
        else:
            username = self.run_as.username
        inv = JMSInventory(self.allow_assets, run_as=username, system_user=self.run_as)
        return inv

    @lazyproperty
    def run_as_display(self):
        return str(self.run_as)

    @lazyproperty
    def user_display(self):
        return str(self.user)

    @lazyproperty
    def hosts_display(self):
        return ','.join(self.hosts.all().values_list('hostname', flat=True))

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

    def cmd_filter_rules(self, asset_id=None):
        from assets.models import CommandFilterRule
        user_id = self.user.id
        system_user_id = self.run_as.id
        rules = CommandFilterRule.get_queryset(
            user_id=user_id,
            system_user_id=system_user_id,
            asset_id=asset_id,
        )
        return rules

    def is_command_can_run(self, command, asset_id=None):
        for rule in self.cmd_filter_rules(asset_id=asset_id):
            action, matched_cmd = rule.match(command)
            if action == rule.ActionChoices.allow:
                return True, None
            elif action == rule.ActionChoices.deny:
                return False, matched_cmd
        return True, None

    @property
    def allow_assets(self):
        allow_asset_ids = []
        for asset in self.hosts.all():
            ok, __ = self.is_command_can_run(self.command, asset_id=asset.id)
            if ok:
                allow_asset_ids.append(asset.id)
        allow_assets = Asset.objects.filter(id__in=allow_asset_ids)
        return allow_assets

    def run(self):
        print('-' * 10 + ' ' + ugettext('Task start') + ' ' + '-' * 10)
        org = Organization.get_instance(self.run_as.org_id)
        org.change_to()
        self.date_start = timezone.now()
        ok, msg = self.is_command_can_run(self.command)
        if ok:
            allow_assets = self.allow_assets
            deny_assets = set(list(self.hosts.all())) - set(list(allow_assets))
            for asset in deny_assets:
                print(f'资产{asset}: 命令{self.command}不允许执行')
            if not allow_assets:
                self.result = {
                    "error": 'There are currently no assets that can be executed'
                }
                self.save()
                return self.result
            runner = CommandRunner(self.inventory)
            try:
                host = allow_assets.first()
                if host and host.is_windows():
                    shell = 'win_shell'
                elif host and host.is_unixlike():
                    shell = 'shell'
                else:
                    shell = 'raw'
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
            CommandExecutionAlert({
                'input': self.command,
                'assets': self.hosts.all(),
                'user': str(self.user),
                'risk_level': 5,
            }).publish_async()
            self.result = {"error": msg}
        self.org_id = self.run_as.org_id
        self.is_finished = True
        self.date_finished = timezone.now()
        self.save()
        print('-' * 10 + ' ' + ugettext('Task end') + ' ' + '-' * 10)
        return self.result

    class Meta:
        verbose_name = _("Command execution")
