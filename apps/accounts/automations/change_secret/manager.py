import os
import time
from copy import deepcopy

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from xlsxwriter import Workbook

from accounts.const import (
    AutomationTypes, SecretType, SSHKeyStrategy, SecretStrategy, ChangeSecretRecordStatusChoice
)
from accounts.models import ChangeSecretRecord, BaseAccountQuerySet
from accounts.notifications import ChangeSecretExecutionTaskMsg, ChangeSecretFailedMsg
from accounts.serializers import ChangeSecretRecordBackUpSerializer
from assets.const import HostTypes
from common.db.utils import safe_db_connection
from common.decorators import bulk_create_decorator
from common.utils import get_logger
from common.utils.file import encrypt_and_compress_zip_file
from common.utils.timezone import local_now_filename
from ..base.manager import AccountBasePlaybookManager
from ...utils import SecretGenerator

logger = get_logger(__name__)


class ChangeSecretManager(AccountBasePlaybookManager):
    ansible_account_prefer = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.record_map = self.execution.snapshot.get('record_map', {})  # 这个是某个失败的记录重试
        self.secret_type = self.execution.snapshot.get('secret_type')
        self.secret_strategy = self.execution.snapshot.get(
            'secret_strategy', SecretStrategy.custom
        )
        self.ssh_key_change_strategy = self.execution.snapshot.get(
            'ssh_key_change_strategy', SSHKeyStrategy.set_jms
        )
        self.account_ids = self.execution.snapshot['accounts']
        self.name_recorder_mapper = {}  # 做个映射，方便后面处理
        self.pending_add_records = []

    @classmethod
    def method_type(cls):
        return AutomationTypes.change_secret

    def get_ssh_params(self, account, secret, secret_type):
        kwargs = {}
        if secret_type != SecretType.SSH_KEY:
            return kwargs
        kwargs['strategy'] = self.ssh_key_change_strategy
        kwargs['exclusive'] = 'yes' if kwargs['strategy'] == SSHKeyStrategy.set else 'no'

        if kwargs['strategy'] == SSHKeyStrategy.set_jms:
            kwargs['regexp'] = '.*{}$'.format(secret.split()[2].strip())
        return kwargs

    def get_accounts(self, privilege_account) -> BaseAccountQuerySet | None:
        if not privilege_account:
            print('Not privilege account')
            return

        asset = privilege_account.asset
        accounts = asset.accounts.all()
        accounts = accounts.filter(id__in=self.account_ids)
        if self.secret_type:
            accounts = accounts.filter(secret_type=self.secret_type)

        if settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED:
            accounts = accounts.filter(privileged=False).exclude(
                username__in=['root', 'administrator', privilege_account.username]
            )
        return accounts

    def gen_new_secret(self, account, path_dir):
        private_key_path = None
        if self.secret_type is None:
            new_secret = account.secret
            return new_secret, private_key_path

        if self.secret_strategy == SecretStrategy.custom:
            new_secret = self.execution.snapshot['secret']
        else:
            generator = SecretGenerator(
                self.secret_strategy, self.secret_type,
                self.execution.snapshot.get('password_rules')
            )
            new_secret = generator.get_secret()

        if account.secret_type == SecretType.SSH_KEY:
            private_key_path = self.generate_private_key_path(new_secret, path_dir)
            new_secret = self.generate_public_key(new_secret)
        return new_secret, private_key_path

    def get_or_create_record(self, asset, account, new_secret, name):
        asset_account_id = f'{asset.id}-{account.id}'

        if asset_account_id in self.record_map:
            record_id = self.record_map[asset_account_id]
            recorder = ChangeSecretRecord.objects.filter(id=record_id).first()
        else:
            recorder = self.create_record(asset, account, new_secret)

        if recorder:
            self.name_recorder_mapper[name] = recorder

    @bulk_create_decorator(ChangeSecretRecord)
    def create_record(self, asset, account, new_secret):
        recorder = ChangeSecretRecord(
            asset=asset, account=account, execution=self.execution,
            old_secret=account.secret, new_secret=new_secret,
            comment=f'{account.username}@{asset.address}'
        )
        return recorder

    def gen_change_secret_inventory(self, host, account, new_secret, private_key_path, asset):
        h = deepcopy(host)
        secret_type = account.secret_type
        h['name'] += '(' + account.username + ')'
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
        return h

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(
            host, asset=asset, account=account, automation=automation,
            path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            return host

        host['check_conn_after_change'] = self.execution.snapshot.get('check_conn_after_change', True)
        host['ssh_params'] = {}

        accounts = self.get_accounts(account)
        error_msg = _("! No pending accounts found")
        if not accounts:
            print(f'{asset}: {error_msg}')
            return []

        if asset.type == HostTypes.WINDOWS:
            accounts = accounts.filter(secret_type=SecretType.PASSWORD)

        inventory_hosts = []
        if asset.type == HostTypes.WINDOWS and self.secret_type == SecretType.SSH_KEY:
            print(f'! Windows {asset} does not support ssh key push')
            return inventory_hosts

        for account in accounts:
            new_secret, private_key_path = self.gen_new_secret(account, path_dir)
            h = self.gen_change_secret_inventory(host, account, new_secret, private_key_path, asset)
            self.get_or_create_record(asset, account, new_secret, h['name'])
            inventory_hosts.append(h)

        return inventory_hosts

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

        account.secret = recorder.new_secret
        account.date_updated = timezone.now()

        with safe_db_connection():
            recorder.save(update_fields=['status', 'date_finished'])
            account.save(update_fields=['secret', 'version', 'date_updated'])

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

    def on_runner_failed(self, runner, e, **kwargs):
        logger.error("Account error: ", e)

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

        failed_recorders = [
            r for r in recorders
            if r.status == ChangeSecretRecordStatusChoice.failed.value
        ]

        recipients = self.execution.recipients
        if not recipients:
            return

        if failed_recorders:
            name = self.execution.snapshot.get('name')
            execution_id = str(self.execution.id)
            _ids = [r.id for r in failed_recorders]
            asset_account_errors = ChangeSecretRecord.objects.filter(
                id__in=_ids).values_list('asset__name', 'account__username', 'error')

            for user in recipients:
                ChangeSecretFailedMsg(name, execution_id, user, asset_account_errors).publish()

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
