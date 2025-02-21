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
from common.decorators import bulk_create_decorator
from common.utils import get_logger
from common.utils.file import encrypt_and_compress_zip_file
from common.utils.timezone import local_now_filename
from ..base.manager import BaseChangeSecretPushManager
from ...utils import SecretGenerator

logger = get_logger(__name__)


class ChangeSecretManager(BaseChangeSecretPushManager):
    ansible_account_prefer = ''

    @classmethod
    def method_type(cls):
        return AutomationTypes.change_secret

    def get_secret(self, account):
        if self.secret_strategy == SecretStrategy.custom:
            new_secret = self.execution.snapshot['secret']
        else:
            generator = SecretGenerator(
                self.secret_strategy, self.secret_type,
                self.execution.snapshot.get('password_rules')
            )
            new_secret = generator.get_secret()
        return new_secret

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

    @bulk_create_decorator(ChangeSecretRecord)
    def create_record(self, asset, account, new_secret):
        recorder = ChangeSecretRecord(
            asset=asset, account=account, execution=self.execution,
            old_secret=account.secret, new_secret=new_secret,
            comment=f'{account.username}@{asset.address}'
        )
<<<<<<< HEAD
        if host.get('error'):
            return host

        accounts = self.get_accounts(account)
        error_msg = _("No pending accounts found")
        if not accounts:
            print(f'{asset}: {error_msg}')
            return []

        records = []
        inventory_hosts = []
        if asset.type == HostTypes.WINDOWS and self.secret_type == SecretType.SSH_KEY:
            print(f'Windows {asset} does not support ssh key push')
            return inventory_hosts

        if asset.type == HostTypes.WINDOWS:
            accounts = accounts.filter(secret_type=SecretType.PASSWORD)

        host['ssh_params'] = {}
        for account in accounts:
            h = deepcopy(host)
            secret_type = account.secret_type
            h['name'] += '(' + account.username + ')'
            if self.secret_type is None:
                new_secret = account.secret
            else:
                new_secret = self.get_secret(secret_type)

            if new_secret is None:
                print(f'new_secret is None, account: {account}')
                continue

            asset_account_id = f'{asset.id}-{account.id}'
            if asset_account_id not in self.record_map:
                recorder = ChangeSecretRecord(
                    asset=asset, account=account, execution=self.execution,
                    old_secret=account.secret, new_secret=new_secret,
                    comment=f'{account.username}@{asset.address}'
                )
                records.append(recorder)
            else:
                record_id = self.record_map[asset_account_id]
                try:
                    recorder = ChangeSecretRecord.objects.get(id=record_id)
                except ChangeSecretRecord.DoesNotExist:
                    print(f"Record {record_id} not found")
                    continue

            self.name_recorder_mapper[h['name']] = recorder

            private_key_path = None
            if secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(new_secret, path_dir)
                new_secret = self.generate_public_key(new_secret)

            h['ssh_params'].update(self.get_ssh_params(account, new_secret, secret_type))
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': secret_type,
                'secret': account.escape_jinja2_syntax(new_secret),
                'private_key_path': private_key_path,
                'become': account.get_ansible_become_auth(),
            }
            if asset.platform.type == 'oracle':
                h['account']['mode'] = 'sysdba' if account.privileged else None
            inventory_hosts.append(h)
        ChangeSecretRecord.objects.bulk_create(records)
        return inventory_hosts

    @staticmethod
    def require_update_version(account, recorder):
        return account.secret != recorder.new_secret

    def on_host_success(self, host, result):
        recorder = self.name_recorder_mapper.get(host)
        if not recorder:
            return
        recorder.status = ChangeSecretRecordStatusChoice.success.value
        recorder.date_finished = timezone.now()

        account = recorder.account
        if not account:
            print("Account not found, deleted ?")
            return

        version_update_required = self.require_update_version(account, recorder)
        account.secret = recorder.new_secret
        account.date_updated = timezone.now()

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                recorder.save()
                account_update_fields = ['secret', 'date_updated']
                if version_update_required:
                    account_update_fields.append('version')
                account.save(update_fields=account_update_fields)
                break
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    self.on_host_error(host, str(e), result)
                else:
                    print(f'retry {retry_count} times for {host} recorder save error: {e}')
                    time.sleep(1)

    def on_host_error(self, host, error, result):
        recorder = self.name_recorder_mapper.get(host)
        if not recorder:
            return
        recorder.status = ChangeSecretRecordStatusChoice.failed.value
        recorder.date_finished = timezone.now()
        recorder.error = error
        try:
            recorder.save()
        except Exception as e:
            print(f"\033[31m Save {host} recorder error: {e} \033[0m\n")

    def on_runner_failed(self, runner, e):
        logger.error("Account error: ", e)
=======
        return recorder
>>>>>>> pam

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
