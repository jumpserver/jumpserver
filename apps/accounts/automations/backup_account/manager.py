# -*- coding: utf-8 -*-
#

from django.utils.translation import gettext_lazy as _

from assets.automations.base.manager import BaseManager
from common.utils.timezone import local_now_display
from .handlers import AccountBackupHandler


class AccountBackupManager(BaseManager):
    def do_run(self):
        execution = self.execution
        account_backup_execution_being_executed = _('The account backup plan is being executed')
        print(f'\033[33m# {account_backup_execution_being_executed}\033[0m')
        handler = AccountBackupHandler(self, execution)
        handler.run()

    def send_report_if_need(self):
        pass

    def print_summary(self):
        print('\n\n' + '-' * 80)
        plan_execution_end = _('Plan execution end')
        print('{} {}\n'.format(plan_execution_end, local_now_display()))
        time_cost = _('Duration')
        print('{}: {}s'.format(time_cost, self.duration))

    def get_report_template(self):
        return "accounts/backup_account_report.html"
