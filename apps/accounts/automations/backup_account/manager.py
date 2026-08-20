# -*- coding: utf-8 -*-
#

from django.utils.translation import gettext_lazy as _

from assets.automations.base.manager import BaseManager
from common.const import Status
from .handlers import AccountBackupHandler


class AccountBackupManager(BaseManager):
    def do_run(self):
        execution = self.execution
        account_backup_execution_being_executed = _('The account backup plan is being executed')
        self.print_log(account_backup_execution_being_executed, 'progress')
        handler = AccountBackupHandler(self, execution)
        handler.run()

    def send_report_if_need(self):
        pass

    def print_summary(self):
        error = self.summary.get('error')
        self.print_log(
            _("Task execution completed"),
            'error'
            if error or self.status in (Status.failed, Status.error)
            else 'success',
        )
        if error:
            self.print_log(
                _("Backup failed: %(error)s") % {'error': error}, 'error'
            )
        else:
            self.print_log(_("Backed up %(count)s accounts") % {
                'count': self.summary.get('total_accounts', 0),
            }, 'success')
        self.print_log(_("Duration: %(duration)s seconds") % {
            'duration': self.duration,
        }, 'info')

    def get_report_template(self):
        return "accounts/backup_account_report.html"
