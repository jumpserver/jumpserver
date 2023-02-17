import os
import time
from collections import defaultdict
from copy import deepcopy

from django.conf import settings
from django.utils import timezone
from openpyxl import Workbook

from accounts.const import AutomationTypes, SecretType, SSHKeyStrategy, SecretStrategy
from accounts.models import ChangeSecretRecord
from accounts.notifications import ChangeSecretExecutionTaskMsg
from accounts.serializers import ChangeSecretRecordBackUpSerializer
from common.utils import get_logger, lazyproperty
from common.utils.file import encrypt_and_compress_zip_file
from common.utils.timezone import local_now_display
from users.models import User
from ..base.manager import AccountBasePlaybookManager
from ...utils import SecretGenerator

logger = get_logger(__name__)


class ChangeSecretManager(AccountBasePlaybookManager):
    ansible_account_prefer = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.method_hosts_mapper = defaultdict(list)
        self.secret_type = self.execution.snapshot['secret_type']
        self.secret_strategy = self.execution.snapshot.get(
            'secret_strategy', SecretStrategy.custom
        )
        self.ssh_key_change_strategy = self.execution.snapshot.get(
            'ssh_key_change_strategy', SSHKeyStrategy.add
        )
        self.snapshot_account_usernames = self.execution.snapshot['accounts']
        self.name_recorder_mapper = {}  # 做个映射，方便后面处理

    @classmethod
    def method_type(cls):
        return AutomationTypes.change_secret

    def get_kwargs(self, account, secret):
        kwargs = {}
        if self.secret_type != SecretType.SSH_KEY:
            return kwargs
        kwargs['strategy'] = self.ssh_key_change_strategy
        kwargs['exclusive'] = 'yes' if kwargs['strategy'] == SSHKeyStrategy.set else 'no'

        if kwargs['strategy'] == SSHKeyStrategy.set_jms:
            kwargs['dest'] = '/home/{}/.ssh/authorized_keys'.format(account.username)
            kwargs['regexp'] = '.*{}$'.format(secret.split()[2].strip())
        return kwargs

    @lazyproperty
    def secret_generator(self):
        return SecretGenerator(
            self.secret_strategy, self.secret_type,
            self.execution.snapshot.get('password_rules')
        )

    def get_secret(self):
        if self.secret_strategy == SecretStrategy.custom:
            return self.execution.snapshot['secret']
        else:
            return self.secret_generator.get_secret()

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

        accounts = asset.accounts.all()
        if account:
            accounts = accounts.exclude(username=account.username)

        if '*' not in self.snapshot_account_usernames:
            accounts = accounts.filter(username__in=self.snapshot_account_usernames)

        accounts = accounts.filter(secret_type=self.secret_type)
        method_attr = getattr(automation, self.method_type() + '_method')
        method_hosts = self.method_hosts_mapper[method_attr]
        method_hosts = [h for h in method_hosts if h != host['name']]
        inventory_hosts = []
        records = []
        host['secret_type'] = self.secret_type
        for account in accounts:
            h = deepcopy(host)
            h['name'] += '_' + account.username
            new_secret = self.get_secret()

            recorder = ChangeSecretRecord(
                asset=asset, account=account, execution=self.execution,
                old_secret=account.secret, new_secret=new_secret,
            )
            records.append(recorder)
            self.name_recorder_mapper[h['name']] = recorder

            private_key_path = None
            if self.secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(new_secret, path_dir)
                new_secret = self.generate_public_key(new_secret)

            h['kwargs'] = self.get_kwargs(account, new_secret)
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': new_secret,
                'private_key_path': private_key_path
            }
            if asset.platform.type == 'oracle':
                h['account']['mode'] = 'sysdba' if account.privileged else None
            inventory_hosts.append(h)
            method_hosts.append(h['name'])
        self.method_hosts_mapper[method_attr] = method_hosts
        ChangeSecretRecord.objects.bulk_create(records)
        return inventory_hosts

    def on_host_success(self, host, result):
        recorder = self.name_recorder_mapper.get(host)
        if not recorder:
            return
        recorder.status = 'success'
        recorder.date_finished = timezone.now()
        recorder.save()
        print('recorder.new_secret', recorder.new_secret)
        account = recorder.account
        account.secret = recorder.new_secret
        account.save(update_fields=['secret'])

    def on_host_error(self, host, error, result):
        recorder = self.name_recorder_mapper.get(host)
        if not recorder:
            return
        recorder.status = 'failed'
        recorder.date_finished = timezone.now()
        recorder.error = error
        recorder.save()

    def on_runner_failed(self, runner, e):
        logger.error("Change secret error: ", e)

    def check_secret(self):
        if self.secret_strategy == SecretStrategy.custom \
                and not self.execution.snapshot['secret']:
            print('Custom secret is empty')
            return False
        return True

    def run(self, *args, **kwargs):
        if not self.check_secret():
            return
        super().run(*args, **kwargs)
        recorders = self.name_recorder_mapper.values()
        recorders = list(recorders)
        self.send_recorder_mail(recorders)

    def send_recorder_mail(self, recorders):
        recipients = self.execution.recipients
        if not recorders or not recipients:
            return

        recipients = User.objects.filter(id__in=list(recipients.keys()))

        name = self.execution.snapshot['name']
        path = os.path.join(os.path.dirname(settings.BASE_DIR), 'tmp')
        filename = os.path.join(path, f'{name}-{local_now_display()}-{time.time()}.xlsx')
        if not self.create_file(recorders, filename):
            return

        for user in recipients:
            attachments = []
            if user.secret_key:
                password = user.secret_key.encode('utf8')
                attachment = os.path.join(path, f'{name}-{local_now_display()}-{time.time()}.zip')
                encrypt_and_compress_zip_file(attachment, password, [filename])
                attachments = [attachment]
            ChangeSecretExecutionTaskMsg(name, user).publish(attachments)
        os.remove(filename)

    @staticmethod
    def create_file(recorders, filename):
        serializer_cls = ChangeSecretRecordBackUpSerializer
        serializer = serializer_cls(recorders, many=True)

        header = [str(v.label) for v in serializer.child.fields.values()]
        rows = [list(row.values()) for row in serializer.data]
        if not rows:
            return False

        rows.insert(0, header)
        wb = Workbook(filename)
        ws = wb.create_sheet('Sheet1')
        for row in rows:
            ws.append(row)
        wb.save(filename)
        return True
