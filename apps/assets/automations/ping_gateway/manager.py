import socket

import paramiko
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from assets.const import AutomationTypes, Connectivity
from assets.models import Gateway
from common.utils import get_logger

logger = get_logger(__name__)


class PingGatewayManager:

    def __init__(self, execution):
        self.execution = execution

    @classmethod
    def method_type(cls):
        return AutomationTypes.ping_gateway

    def execute_task(self, gateway, account):
        from accounts.models import Account
        local_port = self.execution.snapshot.get('local_port')
        local_port = gateway.port if local_port is None else local_port
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        proxy = paramiko.SSHClient()
        proxy.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if not isinstance(account, Account):
            err = _('No account')
            return False, err

        print('- ' + _('Asset, {}, using account {}').format(gateway, account))
        try:
            proxy.connect(
                gateway.address,
                port=gateway.port,
                username=account.username,
                password=account.secret,
                pkey=account.private_key_obj
            )
        except(
                paramiko.AuthenticationException,
                paramiko.BadAuthenticationType,
                paramiko.SSHException,
                paramiko.ChannelException,
                paramiko.ssh_exception.NoValidConnectionsError,
                socket.gaierror
        ) as e:
            err = str(e)
            if err.startswith('[Errno None] Unable to connect to port'):
                err = _('Unable to connect to port {port} on {address}')
                err = err.format(port=gateway.port, address=gateway.address)
            elif err == 'Authentication failed.':
                err = _('Authentication failed')
            elif err == 'Connect failed':
                err = _('Connect failed')
            return False, err

        try:
            sock = proxy.get_transport().open_channel(
                'direct-tcpip', ('127.0.0.1', local_port), ('127.0.0.1', 0)
            )
            client.connect(
                '127.0.0.1',
                sock=sock,
                timeout=5,
                port=local_port,
                username=account.username,
                password=account.secret,
                key_filename=account.private_key_path,
            )
        except (
                paramiko.SSHException,
                paramiko.ssh_exception.SSHException,
                paramiko.ChannelException,
                paramiko.AuthenticationException,
                TimeoutError
        ) as e:

            err = getattr(e, 'text', str(e))
            if err == 'Connect failed':
                err = _('Connect failed')
            return False, err
        finally:
            client.close()
        return True, None

    @staticmethod
    def on_host_success(gateway, account):
        print('\033[32m {} -> {}\033[0m\n'.format(gateway, account))
        gateway.set_connectivity(Connectivity.OK)
        if not account:
            return
        account.set_connectivity(Connectivity.OK)

    @staticmethod
    def on_host_error(gateway, account, error):
        print('\033[31m {} -> {} 原因: {} \033[0m\n'.format(gateway, account, error))
        gateway.set_connectivity(Connectivity.ERR)
        if not account:
            return
        account.set_connectivity(Connectivity.ERR)

    @staticmethod
    def before_runner_start():
        print(">>> 开始执行测试网关可连接性任务")

    def get_accounts(self, gateway):
        account = gateway.select_account
        return [account]

    def run(self):
        asset_ids = self.execution.snapshot['assets']
        gateways = Gateway.objects.filter(id__in=asset_ids)
        self.execution.date_start = timezone.now()
        self.before_runner_start()

        for gateway in gateways:
            accounts = self.get_accounts(gateway)
            for account in accounts:
                ok, e = self.execute_task(gateway, account)
                if ok:
                    self.on_host_success(gateway, account)
                else:
                    self.on_host_error(gateway, account, e)
                print('\n')
        self.execution.status = 'success'
        self.execution.date_finished = timezone.now()
        self.execution.save()
