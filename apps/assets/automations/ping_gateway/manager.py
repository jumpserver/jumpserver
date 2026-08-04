import time

import paramiko
from celery import current_task
from celery.worker import state as celery_worker_state
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from assets.const import AutomationTypes, Connectivity
from assets.models import Gateway
from common.const import Status
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
        if not isinstance(account, Account):
            err = _('No account')
            return False, err

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        proxy = paramiko.SSHClient()
        proxy.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_timeout = max(
            int(getattr(settings, 'SSH_GATEWAY_CONNECT_TIMEOUT', 30) or 30),
            1,
        )

        print('- ' + _('Asset, {}, using account {}').format(gateway, account))
        try:
            try:
                private_key = account.private_key_obj
                proxy.connect(
                    gateway.address,
                    port=gateway.port,
                    username=account.username,
                    password=account.secret,
                    pkey=private_key,
                    timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                    auth_timeout=connect_timeout,
                    allow_agent=False,
                    look_for_keys=False,
                )
            except (
                    paramiko.AuthenticationException,
                    paramiko.BadAuthenticationType,
                    paramiko.SSHException,
                    paramiko.ChannelException,
                    paramiko.ssh_exception.NoValidConnectionsError,
                    OSError,
                    EOFError,
            ) as e:
                err = str(e)
                if err.startswith('[Errno None] Unable to connect to port'):
                    err = _('Unable to connect to port {port} on {address}')
                    err = err.format(
                        port=gateway.port, address=gateway.address
                    )
                elif err == 'Authentication failed.':
                    err = _('Authentication failed')
                elif err == 'Connect failed':
                    err = _('Connect failed')
                return False, err

            try:
                transport = proxy.get_transport()
                if not transport or not transport.is_active():
                    return False, _('Connect failed')
                sock = transport.open_channel(
                    'direct-tcpip',
                    ('127.0.0.1', local_port),
                    ('127.0.0.1', 0),
                    timeout=connect_timeout,
                )
                client.connect(
                    '127.0.0.1',
                    sock=sock,
                    timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                    auth_timeout=connect_timeout,
                    port=local_port,
                    username=account.username,
                    password=account.secret,
                    pkey=private_key,
                    allow_agent=False,
                    look_for_keys=False,
                )
            except (
                    paramiko.SSHException,
                    paramiko.ChannelException,
                    paramiko.AuthenticationException,
                    OSError,
                    EOFError,
            ) as e:
                err = getattr(e, 'text', str(e))
                if err == 'Connect failed':
                    err = _('Connect failed')
                return False, err
            return True, None
        except Exception as error:
            logger.exception(
                'Unexpected gateway connectivity error: gateway=%s account=%s',
                gateway.id, account.id,
            )
            return False, str(error)
        finally:
            client.close()
            proxy.close()

    @staticmethod
    def on_host_success(gateway, account):
        print('\033[32m {} -> {}\033[0m\n'.format(gateway, account))
        try:
            gateway.set_connectivity(Connectivity.OK)
            if not account:
                return
            account.set_connectivity(Connectivity.OK)
        except Exception as e:
            print(f'\033[31m Update account {getattr(account, "name", "-")} or '
                  f'update asset {gateway.name} connectivity failed: {e} \033[0m\n')
            return str(e)
        return None

    @staticmethod
    def on_host_error(gateway, account, error):
        print('\033[31m {} -> {} 原因: {} \033[0m\n'.format(gateway, account, error))
        try:
            gateway.set_connectivity(Connectivity.ERR)
            if not account:
                return
            account.set_connectivity(Connectivity.ERR)
        except Exception as e:
            print(f'\033[31m Update account {getattr(account, "name", "-")} or '
                  f'update asset {gateway.name} connectivity failed: {e} \033[0m\n')
            return str(e)
        return None

    @staticmethod
    def before_runner_start():
        print(_(">>> Start executing the task to test gateway connectivity"))

    def get_accounts(self, gateway):
        account = gateway.select_account
        return [account]

    @staticmethod
    def is_celery_task_revoked():
        try:
            task_id = current_task.request.id
        except Exception:
            return False
        return bool(task_id and task_id in celery_worker_state.revoked)

    def run(self):
        time_start = time.monotonic()
        asset_ids = {
            str(asset_id)
            for asset_id in self.execution.snapshot.get('assets', [])
        }
        gateways = list(Gateway.objects.filter(id__in=asset_ids))
        self.execution.date_start = timezone.now()
        self.execution.status = Status.running
        self.execution.save(update_fields=['date_start', 'status'])
        self.before_runner_start()

        failed = 0
        result = {'ok': [], 'failed': []}
        found_gateway_ids = {str(gateway.id) for gateway in gateways}
        for gateway_id in sorted(asset_ids - found_gateway_ids):
            failed += 1
            result['failed'].append({
                'gateway': gateway_id,
                'error': str(_('Gateway not found or inactive')),
            })

        final_status = Status.success
        total_timeout = int(
            getattr(settings, 'ANSIBLE_AUTOMATION_TOTAL_TIMEOUT', 21600)
            or 0
        )
        for gateway in gateways:
            if self.is_celery_task_revoked():
                final_status = Status.canceled
                result['interruption'] = str(_('Task canceled by user'))
                break
            if (
                    total_timeout > 0
                    and time.monotonic() - time_start >= total_timeout
            ):
                final_status = Status.error
                result['interruption'] = str(_('Task execution timed out'))
                break

            try:
                accounts = list(self.get_accounts(gateway))
            except Exception as error:
                logger.exception(
                    'Load gateway accounts failed: gateway=%s', gateway.id
                )
                failed += 1
                result['failed'].append({
                    'gateway': str(gateway),
                    'error': str(error),
                })
                continue
            if not accounts:
                error = str(_('No account'))
                self.on_host_error(gateway, None, error)
                failed += 1
                result['failed'].append({
                    'gateway': str(gateway),
                    'error': error,
                })
                continue
            for account in accounts:
                if self.is_celery_task_revoked():
                    final_status = Status.canceled
                    result['interruption'] = str(_('Task canceled by user'))
                    break
                if (
                        total_timeout > 0
                        and time.monotonic() - time_start >= total_timeout
                ):
                    final_status = Status.error
                    result['interruption'] = str(
                        _('Task execution timed out')
                    )
                    break
                ok, e = self.execute_task(gateway, account)
                if ok:
                    save_error = self.on_host_success(gateway, account)
                    if save_error:
                        ok = False
                        e = _(
                            'Connectivity succeeded but saving the result '
                            'failed: {error}'
                        ).format(error=save_error)
                    else:
                        result['ok'].append(str(gateway))
                if not ok:
                    if e:
                        self.on_host_error(gateway, account, e)
                    failed += 1
                    result['failed'].append({
                        'gateway': str(gateway),
                        'error': str(e),
                    })
                print('\n')
            if final_status != Status.success:
                break
        if final_status == Status.success and failed:
            final_status = Status.failed
        self.execution.status = final_status
        self.execution.date_finished = timezone.now()
        self.execution.duration = round(time.monotonic() - time_start, 2)
        self.execution.summary = {
            'total': len(result['ok']) + failed,
            'ok': len(result['ok']),
            'failed': failed,
        }
        self.execution.result = result
        self.execution.save(update_fields=[
            'status', 'date_finished', 'duration', 'summary', 'result',
        ])
