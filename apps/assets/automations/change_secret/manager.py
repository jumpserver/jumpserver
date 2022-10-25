import os
import random
import string
from hashlib import md5
from copy import deepcopy
from socket import gethostname
from collections import defaultdict

from django.utils import timezone

from common.utils import lazyproperty, gen_key_pair, ssh_pubkey_gen, ssh_key_string_to_obj
from assets.models import ChangeSecretRecord
from assets.const import (
    AutomationTypes, SecretType, SecretStrategy, SSHKeyStrategy, DEFAULT_PASSWORD_RULES
)
from ..base.manager import BasePlaybookManager


class ChangeSecretManager(BasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.method_hosts_mapper = defaultdict(list)
        self.secret_type = self.execution.snapshot['secret_type']
        self.secret_strategy = self.execution.snapshot['secret_strategy']
        self._password_generated = None
        self._ssh_key_generated = None
        self.name_recorder_mapper = {}  # 做个映射，方便后面处理

    @classmethod
    def method_type(cls):
        return AutomationTypes.change_secret

    @lazyproperty
    def related_accounts(self):
        pass

    @staticmethod
    def generate_ssh_key():
        private_key, public_key = gen_key_pair()
        return private_key

    @staticmethod
    def generate_public_key(private_key):
        return ssh_pubkey_gen(private_key=private_key, hostname=gethostname())

    @staticmethod
    def generate_private_key_path(secret, path_dir):
        key_name = '.' + md5(secret.encode('utf-8')).hexdigest()
        key_path = os.path.join(path_dir, key_name)
        if not os.path.exists(key_path):
            ssh_key_string_to_obj(secret, password=None).write_private_key_file(key_path)
            os.chmod(key_path, 0o400)
        return key_path

    def generate_password(self):
        kwargs = self.execution.snapshot['password_rules'] or {}
        length = int(kwargs.get('length', DEFAULT_PASSWORD_RULES['length']))
        symbol_set = kwargs.get('symbol_set')
        if symbol_set is None:
            symbol_set = DEFAULT_PASSWORD_RULES['symbol_set']

        no_special_chars = string.ascii_letters + string.digits
        chars = no_special_chars + symbol_set

        first_char = random.choice(no_special_chars)
        password = ''.join([random.choice(chars) for _ in range(length - 1)])
        password = first_char + password
        return password

    def get_ssh_key(self):
        if self.secret_strategy == SecretStrategy.custom:
            secret = self.execution.snapshot['secret']
            if not secret:
                raise ValueError("Automation SSH key must be set")
            return secret
        elif self.secret_strategy == SecretStrategy.random_one:
            if not self._ssh_key_generated:
                self._ssh_key_generated = self.generate_ssh_key()
            return self._ssh_key_generated
        else:
            return self.generate_ssh_key()

    def get_password(self):
        if self.secret_strategy == SecretStrategy.custom:
            password = self.execution.snapshot['secret']
            if not password:
                raise ValueError("Automation Password must be set")
            return password
        elif self.secret_strategy == SecretStrategy.random_one:
            if not self._password_generated:
                self._password_generated = self.generate_password()
            return self._password_generated
        else:
            return self.generate_password()

    def get_secret(self):
        if self.secret_type == SecretType.ssh_key:
            secret = self.get_ssh_key()
        elif self.secret_type == SecretType.password:
            secret = self.get_password()
        else:
            raise ValueError("Secret must be set")
        return secret

    def get_kwargs(self, account, secret):
        kwargs = {}
        if self.secret_type != SecretType.ssh_key:
            return kwargs
        kwargs['strategy'] = self.execution.snapshot['ssh_key_change_strategy']
        kwargs['exclusive'] = 'yes' if kwargs['strategy'] == SSHKeyStrategy.set else 'no'

        if kwargs['strategy'] == SSHKeyStrategy.set_jms:
            kwargs['dest'] = '/home/{}/.ssh/authorized_keys'.format(account.username)
            kwargs['regexp'] = '.*{}$'.format(secret.split()[2].strip())

        return kwargs

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(host, asset=asset, account=account, automation=automation, **kwargs)
        if host.get('error'):
            return host

        accounts = asset.accounts.all()
        if account:
            accounts = accounts.exclude(id=account.id)

        if '*' not in self.execution.snapshot['accounts']:
            accounts = accounts.filter(username__in=self.execution.snapshot['accounts'])

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
                account=account, execution=self.execution,
                old_secret=account.secret, new_secret=new_secret,
            )
            records.append(recorder)
            self.name_recorder_mapper[h['name']] = recorder

            private_key_path = None
            if self.secret_type == SecretType.ssh_key:
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
            inventory_hosts.append(h)
            method_hosts.append(h['name'])
        self.method_hosts_mapper[method_attr] = method_hosts
        ChangeSecretRecord.objects.bulk_create(records)
        return inventory_hosts

    def on_host_success(self, host, result):
        recorder = self.name_recorder_mapper.get(host)
        if not recorder:
            return
        recorder.status = 'succeed'
        recorder.date_finished = timezone.now()
        recorder.save()

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
        pass
