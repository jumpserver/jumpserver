import logging
import time

from celery import current_task
from celery.worker import state as celery_worker_state
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import paramiko
from sshtunnel import (
    BaseSSHTunnelForwarderError, HandlerSSHTunnelForwarderError,
)

from assets.automations.base.manager import print_automation_log
from assets.const import AutomationTypes, Connectivity
from assets.models import Gateway
from common.const import Status
from common.utils import get_logger
from libs.ansible.modules_utils.ssh_tunnel import (
    GatewayConnectTimeout, TimeoutSSHTunnelForwarder,
)

logger = get_logger(__name__)
_ssh_tunnel_logger = logging.Logger(
    f'{__name__}.ssh_tunnel_internal', level=logging.CRITICAL + 1
)
_ssh_tunnel_logger.addHandler(logging.NullHandler())
_ssh_tunnel_logger.propagate = False


class PingGatewayManager:

    def __init__(self, execution):
        self.execution = execution

    @staticmethod
    def format_gateway_target(gateway, account=None):
        name = getattr(gateway, 'name', None) or str(gateway)
        address = getattr(gateway, 'address', None)
        port = getattr(gateway, 'port', None)
        if address and str(address) not in str(name):
            endpoint = f'{address}:{port}' if port else str(address)
            name = f'{name}[{endpoint}]'
        username = getattr(account, 'username', None)
        if username:
            name = f'{name} / {username}'
        return str(name)

    @classmethod
    def method_type(cls):
        return AutomationTypes.ping_gateway

    @staticmethod
    def get_error_message(error, gateway, local_port, phase):
        error_text = str(getattr(error, 'text', None) or error).strip()
        normalized = error_text.lower()

        if (
                'no password or public key available' in normalized
                or 'private key' in normalized
                or 'pkey' in normalized
        ):
            return _(
                'The gateway account has no usable password or private key; '
                'check the gateway account credentials'
            )
        if isinstance(error, GatewayConnectTimeout):
            return _(
                'Gateway connection timed out; check the gateway address, '
                'port, and network'
            )
        if isinstance(error, HandlerSSHTunnelForwarderError):
            return _(
                'Connected to the gateway, but it cannot forward to '
                '127.0.0.1:%(port)s; check the SSH service and port on the '
                'gateway'
            ) % {'port': local_port}
        if isinstance(error, BaseSSHTunnelForwarderError):
            return _(
                'Unable to establish an SSH session to %(address)s:%(port)s; '
                'check the network and gateway account credentials'
            ) % {
                'address': gateway.address,
                'port': gateway.port,
            }
        if isinstance(error, (
                paramiko.AuthenticationException,
                paramiko.BadAuthenticationType,
        )) or 'authentication failed' in normalized:
            if phase == 'forwarded_authentication':
                return _(
                    'The SSH tunnel is available, but gateway account '
                    'authentication through the tunnel failed; check the '
                    'gateway account credentials'
                )
            return _(
                'Gateway account authentication failed; check the gateway '
                'account credentials'
            )
        if isinstance(error, (paramiko.ChannelException,)) or any(
                text in normalized for text in (
                    'connect failed', 'administratively prohibited',
                    'channel open failure',
                )
        ):
            return _(
                'Connected to the gateway, but it cannot forward to '
                '127.0.0.1:%(port)s; check the SSH service and port on the '
                'gateway'
            ) % {'port': local_port}
        if any(text in normalized for text in (
                'name or service not known', 'nodename nor servname',
                'temporary failure in name resolution',
                'unable to resolve ssh gateway',
        )):
            return _(
                'Unable to resolve gateway address %(address)s; check the '
                'address and DNS settings'
            ) % {'address': gateway.address}
        if any(text in normalized for text in (
                'connection refused', 'no valid connections',
                'unable to connect to port', 'network is unreachable',
                'no route to host',
        )):
            return _(
                'Unable to connect to gateway %(address)s:%(port)s; check '
                'the address, port, and network'
            ) % {
                'address': gateway.address,
                'port': gateway.port,
            }
        if not error_text:
            error_text = str(_('Unknown error'))
        return _('Gateway check failed: %(error)s') % {
            'error': error_text.splitlines()[0][:240],
        }

    def execute_task(self, gateway, account):
        from accounts.models import Account
        local_port = self.execution.snapshot.get('local_port')
        local_port = gateway.port if local_port is None else local_port
        if not isinstance(account, Account):
            err = _('No account')
            return False, err

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        tunnel = None
        connect_timeout = max(
            int(getattr(settings, 'SSH_GATEWAY_CONNECT_TIMEOUT', 30) or 30),
            1,
        )

        print_automation_log(
            _("Checking SSH login and tunnel forwarding: %(gateway)s") % {
                'gateway': self.format_gateway_target(gateway, account),
            },
            'progress',
        )
        try:
            try:
                private_key = account.private_key_obj
                tunnel = TimeoutSSHTunnelForwarder(
                    (gateway.address, gateway.port),
                    ssh_username=account.username,
                    ssh_password=account.secret,
                    ssh_pkey=private_key,
                    connect_timeout=connect_timeout,
                    remote_bind_address=('127.0.0.1', local_port),
                    local_bind_address=('127.0.0.1', 0),
                    allow_agent=False,
                    logger=_ssh_tunnel_logger,
                )
                tunnel.start()
            except (
                    paramiko.AuthenticationException,
                    paramiko.BadAuthenticationType,
                    paramiko.SSHException,
                    paramiko.ChannelException,
                    paramiko.ssh_exception.NoValidConnectionsError,
                    BaseSSHTunnelForwarderError,
                    GatewayConnectTimeout,
                    OSError,
                    EOFError,
                    ValueError,
            ) as e:
                return False, self.get_error_message(
                    e, gateway, local_port, 'tunnel_setup'
                )

            try:
                client.connect(
                    '127.0.0.1',
                    timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                    auth_timeout=connect_timeout,
                    port=tunnel.local_bind_port,
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
                    paramiko.BadAuthenticationType,
                    OSError,
                    EOFError,
            ) as e:
                return False, self.get_error_message(
                    e, gateway, local_port, 'forwarded_authentication'
                )
            return True, None
        except Exception as error:
            logger.exception(
                'Unexpected gateway connectivity error: gateway=%s account=%s',
                gateway.id, account.id,
            )
            return False, self.get_error_message(
                error, gateway, local_port, 'unexpected'
            )
        finally:
            client.close()
            if tunnel:
                try:
                    tunnel.stop(force=True)
                except Exception:
                    logger.exception(
                        'Clean gateway tunnel failed: gateway=%s',
                        gateway.id,
                    )

    @classmethod
    def on_host_success(cls, gateway, account):
        print_automation_log(
            _(
                "✓ %(gateway)s: SSH login and tunnel forwarding are available"
            ) % {'gateway': cls.format_gateway_target(gateway, account)},
            'success',
        )
        try:
            gateway.set_connectivity(Connectivity.OK)
            if not account:
                return
            account.set_connectivity(Connectivity.OK)
        except Exception as e:
            return str(e)
        return None

    @classmethod
    def print_host_error(cls, gateway, account, error):
        print_automation_log(_("✗ %(gateway)s: %(error)s") % {
            'gateway': cls.format_gateway_target(gateway, account),
            'error': error,
        }, 'error')

    @classmethod
    def on_host_error(cls, gateway, account, error):
        cls.print_host_error(gateway, account, error)
        try:
            gateway.set_connectivity(Connectivity.ERR)
            if not account:
                return
            account.set_connectivity(Connectivity.ERR)
        except Exception as e:
            return str(e)
        return None

    @staticmethod
    def before_runner_start():
        print_automation_log(_("Checking gateway connectivity"), 'progress')

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
            error = str(_('Gateway not found or inactive'))
            failed += 1
            result['failed'].append({
                'gateway': gateway_id,
                'error': error,
            })
            self.print_host_error(gateway_id, None, error)

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
                self.print_host_error(gateway, None, str(error))
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
        final_level = (
            'error' if failed or final_status == Status.error
            else 'progress' if final_status == Status.canceled
            else 'success'
        )
        print_automation_log(_("Task execution completed"), final_level)
        print_automation_log(_("Result: %(result)s") % {
            'result': ', '.join([
                _("Successful: %(count)s") % {
                    'count': len(result['ok']),
                },
                _("Failed: %(count)s") % {'count': failed},
                _("Total: %(count)s") % {
                    'count': len(result['ok']) + failed,
                },
            ]),
        }, final_level)
        print_automation_log(_("Duration: %(duration)s seconds") % {
            'duration': self.execution.duration,
        }, 'info')
