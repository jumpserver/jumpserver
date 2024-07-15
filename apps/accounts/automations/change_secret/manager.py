import os
import time
from copy import deepcopy

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from xlsxwriter import Workbook

from accounts.const import AutomationTypes, SecretType, SSHKeyStrategy, SecretStrategy, ChangeSecretRecordStatusChoice
from accounts.models import ChangeSecretRecord
from accounts.notifications import ChangeSecretExecutionTaskMsg, ChangeSecretFailedMsg
from accounts.serializers import ChangeSecretRecordBackUpSerializer
from assets.const import HostTypes
from common.utils import get_logger
from common.utils.file import encrypt_and_compress_zip_file
from common.utils.timezone import local_now_filename
from users.models import User
from ..base.manager import AccountBasePlaybookManager
from ...utils import SecretGenerator

logger = get_logger(__name__)


class ChangeSecretManager(AccountBasePlaybookManager):
    ansible_account_prefer = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.record_map = self.execution.snapshot.get('record_map', {})
        self.secret_type = self.execution.snapshot.get('secret_type')
        self.secret_strategy = self.execution.snapshot.get(
            'secret_strategy', SecretStrategy.custom
        )
        self.ssh_key_change_strategy = self.execution.snapshot.get(
            'ssh_key_change_strategy', SSHKeyStrategy.add
        )
        self.account_ids = self.execution.snapshot['accounts']
        self.name_recorder_mapper = {}  # 做个映射，方便后面处理

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
            username = account.username
            path = f'/{username}' if username == "root" else f'/home/{username}'
            kwargs['dest'] = f'{path}/.ssh/authorized_keys'
            kwargs['regexp'] = '.*{}$'.format(secret.split()[2].strip())
        return kwargs

    def secret_generator(self, secret_type):
        return SecretGenerator(
            self.secret_strategy, secret_type,
            self.execution.snapshot.get('password_rules')
        )

    def get_secret(self, secret_type):
        if self.secret_strategy == SecretStrategy.custom:
            return self.execution.snapshot['secret']
        else:
            return self.secret_generator(secret_type).get_secret()

    def get_accounts(self, privilege_account):
        if not privilege_account:
            print(f'not privilege account')
            return []

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

    def host_callback(
            self, host, asset=None, account=None,
            automation=None, path_dir=None, **kwargs
    ):
        host = super().host_callback(
            host, asset=asset, account=account, automation=automation,
            path_dir=path_dir, **kwargs
        )
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

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                recorder.save()
                account.save(update_fields=['secret', 'version', 'date_updated'])
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

    def run(self, *args, **kwargs):
        if self.secret_type and not self.check_secret():
            self.execution.status = 'success'
            self.execution.date_finished = timezone.now()
            self.execution.save()
            return
        super().run(*args, **kwargs)
        recorders = list(self.name_recorder_mapper.values())
        summary = self.get_summary(recorders)
        print(summary, end='')

        if self.record_map:
            return

        failed_recorders = [
            r for r in recorders
            if r.status == ChangeSecretRecordStatusChoice.failed.value
        ]

        recipients = self.execution.recipients
        recipients = User.objects.filter(id__in=list(recipients.keys()))
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
