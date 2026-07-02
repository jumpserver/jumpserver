#!/usr/bin/env python3
import argparse
import json
import os
import signal
import sys
import traceback
from pathlib import Path


def find_root_dir():
    current = Path(__file__).resolve().parent
    for candidate in [current, *current.parents]:
        apps_dir = candidate / 'apps'
        remote_client_file = apps_dir / 'libs' / 'ansible' / 'modules_utils' / 'remote_client.py'
        if remote_client_file.exists():
            return candidate
    raise RuntimeError('Could not locate project root containing apps/libs/ansible/modules_utils/remote_client.py')


ROOT_DIR = find_root_dir()
APPS_DIR = ROOT_DIR / 'apps'
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from libs.ansible.modules_utils.remote_client import SSHClient  # noqa: E402


class DummyModule:
    def __init__(self, params):
        self.params = params

    def fail_json(self, **kwargs):
        raise RuntimeError(kwargs['msg'])


def mask(value):
    return '***' if value else value


def load_inventory(args):
    if args.inventory_file:
        with open(args.inventory_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    if not sys.stdin.isatty():
        return json.load(sys.stdin)

    raise SystemExit('Provide --inventory-file or pipe inventory JSON to stdin.')


def get_target_host(inventory, host_name=None):
    hosts = inventory.get('all', {}).get('hosts', {})
    if host_name:
        try:
            return host_name, hosts[host_name]
        except KeyError as exc:
            available = ', '.join(sorted(hosts))
            raise SystemExit(f'Host {host_name!r} not found. Available: {available}') from exc

    for name, host in hosts.items():
        if name != 'localhost':
            return name, host
    raise SystemExit('No remote hosts found in inventory JSON.')


def build_change_secret_privileged_params(host):
    jms_asset = host['jms_asset']
    jms_account = host['jms_account']
    host_params = host.get('params', {})

    return {
        'login_host': jms_asset['address'],
        'login_port': jms_asset['port'],
        'login_user': jms_account['username'],
        'login_password': jms_account['secret'],
        'login_secret_type': jms_account['secret_type'],
        'login_private_key_path': jms_account['private_key_path'],
        'gateway_args': jms_asset.get('ansible_ssh_common_args', ''),
        'recv_timeout': host_params.get('recv_timeout', 30),
        'delay_time': host_params.get('delay_time', 2),
        'prompt': host_params.get('prompt', '.*'),
        'answers': host_params.get('answers', '.*'),
        'commands': None,
        'become': host.get('jms_custom_become', False),
        'become_method': host.get('jms_custom_become_method', 'su'),
        'become_user': host.get('jms_custom_become_user', ''),
        'become_password': host.get('jms_custom_become_password', ''),
        'become_private_key_path': host.get('jms_custom_become_private_key_path'),
        'old_ssh_version': jms_asset.get('old_ssh_version', False),
    }


def print_effective_params(host_name, params):
    print(f'host = {host_name}')
    print(
        json.dumps(
            {
                'login_host': params['login_host'],
                'login_port': params['login_port'],
                'login_user': params['login_user'],
                'login_password': mask(params['login_password']),
                'login_secret_type': params['login_secret_type'],
                'login_private_key_path': params['login_private_key_path'],
                'become': params['become'],
                'become_method': params['become_method'],
                'become_user': params['become_user'],
                'become_password': mask(params['become_password']),
                'become_private_key_path': params['become_private_key_path'],
                'old_ssh_version': params['old_ssh_version'],
                'gateway_args': params['gateway_args'],
                'recv_timeout': params['recv_timeout'],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def run_with_timeout(timeout, step_name, func):
    if timeout <= 0:
        return func()

    def handler(signum, frame):
        raise TimeoutError(f'{step_name} timed out after {timeout}s')

    previous = signal.signal(signal.SIGALRM, handler)
    try:
        signal.alarm(timeout)
        return func()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def run_client(params, args):
    module = DummyModule(params)
    with SSHClient(module) as client:
        client.connect_params.update(
            {
                'timeout': args.connect_timeout,
                'banner_timeout': args.banner_timeout,
                'auth_timeout': args.auth_timeout,
            }
        )
        print(
            'connect_params =',
            json.dumps(
                {
                    'hostname': client.connect_params.get('hostname'),
                    'port': client.connect_params.get('port'),
                    'username': client.connect_params.get('username'),
                    'password': mask(client.connect_params.get('password')),
                    'key_filename': client.connect_params.get('key_filename'),
                    'transport_factory': getattr(
                        client.connect_params.get('transport_factory'),
                        '__name__',
                        None,
                    ),
                    'timeout': client.connect_params.get('timeout'),
                    'banner_timeout': client.connect_params.get('banner_timeout'),
                    'auth_timeout': client.connect_params.get('auth_timeout'),
                },
                ensure_ascii=False,
            ),
        )
        run_with_timeout(
            args.overall_connect_timeout,
            'SSH connect',
            client.connect,
        )
        if args.command:
            output, error = client.execute([args.command], ['.*'])
            print('command =', args.command)
            print('output =', output)
            print('error =', error)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Debug remote_client.py using JumpServer inventory JSON.',
    )
    parser.add_argument(
        '--inventory-file',
        help='Path to a hosts.json or equivalent inventory JSON file.',
    )
    parser.add_argument(
        '--host',
        help='Inventory host key, for example: dqyhd009010(useradmin)',
    )
    parser.add_argument(
        '--command',
        default='whoami',
        help='Optional command to run after connect(); default: whoami',
    )
    parser.add_argument(
        '--connect-timeout',
        type=int,
        default=10,
        help='Socket connect timeout passed to paramiko.connect(); default: 10',
    )
    parser.add_argument(
        '--banner-timeout',
        type=int,
        default=10,
        help='Banner timeout passed to paramiko.connect(); default: 10',
    )
    parser.add_argument(
        '--auth-timeout',
        type=int,
        default=10,
        help='Authentication timeout passed to paramiko.connect(); default: 10',
    )
    parser.add_argument(
        '--overall-connect-timeout',
        type=int,
        default=20,
        help='Hard timeout around client.connect(); set 0 to disable; default: 20',
    )
    parser.add_argument(
        '--no-debug',
        action='store_true',
        help='Do not enable JMS_REMOTE_CLIENT_DEBUG automatically.',
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.no_debug:
        os.environ.setdefault('JMS_REMOTE_CLIENT_DEBUG', '1')

    inventory = load_inventory(args)
    host_name, host = get_target_host(inventory, args.host)
    params = build_change_secret_privileged_params(host)

    print_effective_params(host_name, params)
    print('flow = ssh as become_user -> su/sudo to login_user')

    try:
        run_client(params, args)
    except Exception as exc:
        print(f'error = {exc}', file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        raise SystemExit(1) from exc


'''
docker cp ./hosts.json jms_core:/opt/jumpserver/
docker cp ./debug_remote_client.py jms_core:/opt/jumpserver/

root@jms_core:/opt/jumpserver# pwd
/opt/jumpserver

dqyhd009010(useradmin) is an example host key from inventory JSON, replace it with your actual host key.

PYTHONPATH=/opt/jumpserver/apps JMS_REMOTE_CLIENT_DEBUG=1 python debug_remote_client.py --inventory-file hosts.json --host 'dqyhd009010(useradmin)' --command 'whoami' --connect-timeout 5 --banner-timeout 5 --auth-timeout 5 --overall-connect-timeout 15
'''

if __name__ == '__main__':
    main()
