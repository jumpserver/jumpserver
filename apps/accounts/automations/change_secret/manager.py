import os
import time

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from xlsxwriter import Workbook

from accounts.const import (
    AutomationTypes, SecretStrategy, ChangeSecretRecordStatusChoice
)
from accounts.models import ChangeSecretRecord
from accounts.notifications import ChangeSecretExecutionTaskMsg, ChangeSecretReportMsg
from accounts.serializers import ChangeSecretRecordBackUpSerializer
from common.utils import get_logger
from common.utils.file import encrypt_and_compress_zip_file
from common.utils.timezone import local_now_filename
from ..base.manager import BaseChangeSecretPushManager

logger = get_logger(__name__)


class ChangeSecretManager(BaseChangeSecretPushManager):
    ansible_account_prefer = ''

    @classmethod
    def method_type(cls):
        return AutomationTypes.change_secret

    def gen_account_inventory(self, account, asset, h, path_dir):
        record = self.get_or_create_record(asset, account, h['name'])
        new_secret, private_key_path = self.handle_ssh_secret(account.secret_type, record.new_secret, path_dir)
        h = self.gen_inventory(h, account, new_secret, private_key_path, asset)
        return h

    def get_or_create_record(self, asset, account, name):
        asset_account_id = f'{asset.id}-{account.id}'

        if asset_account_id in self.record_map:
            record_id = self.record_map[asset_account_id]
            recorder = ChangeSecretRecord.objects.filter(id=record_id).first()
        else:
            new_secret = self.get_secret(account)
            recorder = self.create_record(asset, account, new_secret)

        self.name_recorder_mapper[name] = recorder
        return recorder

    def create_record(self, asset, account, new_secret):
        recorder = ChangeSecretRecord(
            asset=asset, account=account, execution=self.execution,
            old_secret=account.secret, new_secret=new_secret,
            comment=f'{account.username}@{asset.address}'
        )
        return recorder

    def check_secret(self):
        if self.secret_strategy == SecretStrategy.custom \
                and not self.execution.snapshot['secret']:
            print('Custom secret is empty')
            return False
        return True

    @staticmethod
    def get_summary(recorders):
        total, succeed, failed = 0, 0, 0
        for recorder in recorders:
            if recorder.status == ChangeSecretRecordStatusChoice.success.value:
                succeed += 1
            else:
                failed += 1
            total += 1
        summary = _('Success: %s, Failed: %s, Total: %s') % (succeed, failed, total)
        return summary

    def print_summary(self):
        recorders = list(self.name_recorder_mapper.values())
        summary = self.get_summary(recorders)
        print('\n\n' + '-' * 80)
        plan_execution_end = _('Plan execution end')
        print('{} {}\n'.format(plan_execution_end, local_now_filename()))
        time_cost = _('Duration')
        print('{}: {}s'.format(time_cost, self.duration))
        print(summary)

    def send_report_if_need(self, *args, **kwargs):
        if self.secret_type and not self.check_secret():
            return

        recorders = list(self.name_recorder_mapper.values())
        if self.record_map:
            return

        recipients = self.execution.recipients
        if not recipients:
            return

        context = self.get_report_context()
        for user in recipients:
            ChangeSecretReportMsg(user, context).publish()

        if not recorders:
            return

        summary = self.get_summary(recorders)
        self.send_recorder_mail(recipients, recorders, summary)

    def send_recorder_mail(self, recipients, recorders, summary):
        name = self.execution.snapshot['name']
        path = os.path.join(os.path.dirname(settings.BASE_DIR), 'tmp')
        filename = os.path.join(path, f'{name}-{local_now_filename()}-{time.time()}.xlsx')
        if not self.create_file(recorders, filename):
            return

        for user in recipients:
            attachments = []
            if user.secret_key:
                attachment = os.path.join(path, f'{name}-{local_now_filename()}-{time.time()}.zip')
                encrypt_and_compress_zip_file(attachment, user.secret_key, [filename])
                attachments = [attachment]
            ChangeSecretExecutionTaskMsg(name, user, summary).publish(attachments)
        os.remove(filename)

    @staticmethod
    def create_file(recorders, filename):
        serializer_cls = ChangeSecretRecordBackUpSerializer
        serializer = serializer_cls(recorders, many=True)

        header = [str(v.label) for v in serializer.child.fields.values()]
        rows = [[str(i) for i in row.values()] for row in serializer.data]
        if not rows:
            return False

        rows.insert(0, header)
        wb = Workbook(filename)
        ws = wb.add_worksheet('Sheet1')
        for row_index, row_data in enumerate(rows):
            for col_index, col_data in enumerate(row_data):
                ws.write_string(row_index, col_index, col_data)
        wb.close()
        return True

    def get_report_template(self):
        return "accounts/change_secret_report.html"
