import argparse
import json
import os
import pwd
import re
import shlex
import shutil
import socket
import socketserver
import stat
import subprocess
import sys
import tempfile
import threading
import uuid
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

import requests

from . import CONFIG_SCHEMA_VERSION, PROTOCOL_VERSION, __version__
from .common import credential
from .common.exception import (
    REVOKED_CODES, JumpServerPAMSDKException, identity_denied, response_error_code,
)
from .common.profile import client_profile
from .credential.v1 import credential_client, models
from .credential.v1.credential_client import CLIENT_PATH


CONFIG_FILE = '/etc/jumpserver-pam/agent.json'
STATE_FILE = '/var/lib/jumpserver-pam/state.json'
CREDENTIAL_FILE = '/var/lib/jumpserver-pam/credentials.json'
DELIVERY_MODES = frozenset(('json', 'environment', 'socket'))
SYSTEMD_UNIT = re.compile(r'^[A-Za-z0-9_.@:-]+\.service$')


def read_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {} if default is None else default


def atomic_write(path, content, mode=0o600, owner=None):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        raise ValueError('Target path cannot be a symbolic link.')
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', dir=target.parent,
        prefix=f'.{target.name}.', delete=False,
    ) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    try:
        os.chmod(temporary, mode)
        if owner:
            user = pwd.getpwnam(owner)
            os.chown(temporary, user.pw_uid, user.pw_gid)
        if target.is_symlink():
            raise ValueError('Target path cannot be a symbolic link.')
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_write_json(path, data, mode=0o600, owner=None):
    content = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    atomic_write(path, content, mode=mode, owner=owner)


def secure_root(path, mode=0o711):
    target = Path(path)
    if not target.is_absolute() or target == Path('/'):
        raise ValueError('Agent paths must be absolute and cannot be the filesystem root.')
    for item in (target, *target.parents):
        if item.exists() and item.is_symlink():
            raise ValueError('Agent paths cannot contain symbolic links.')
    target.mkdir(parents=True, exist_ok=True)
    info = target.stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Agent output directories must be root-owned and not writable by group or others.')
    os.chmod(target, mode)
    return target.resolve()


def secure_target(root, name):
    root = Path(root).resolve()
    if not isinstance(name, str) or Path(name).name != name:
        raise ValueError('Credential delivery filenames cannot contain path separators.')
    target = root / name
    if target.is_symlink():
        raise ValueError('Credential delivery paths cannot contain symbolic links.')
    target = target.resolve(strict=False)
    if not target.is_relative_to(root) or target == root:
        raise ValueError('Credential delivery escaped its configured root.')
    for item in (target, *target.parents):
        if item == root.parent:
            break
        if item.exists() and item.is_symlink():
            raise ValueError('Credential delivery paths cannot contain symbolic links.')
    return target


def validate_configuration(configuration, capabilities):
    if not isinstance(configuration, dict):
        raise ValueError('Agent configuration must be an object.')
    if configuration.get('delivery_mode') not in DELIVERY_MODES:
        raise ValueError('Unsupported Agent delivery mode.')
    keys = configuration.get('credential_keys')
    if not isinstance(keys, list) or not all(isinstance(key, str) and key for key in keys):
        raise ValueError('Credential keys must be a string list.')
    for field in ('delivery_root', 'socket_path', 'app_user'):
        if configuration.get(field, '') != capabilities.get(field, ''):
            raise ValueError(f'Agent configuration exceeds the installed {field} capability.')
    if configuration['delivery_mode'] == 'environment':
        if not SYSTEMD_UNIT.fullmatch(configuration.get('systemd_unit', '')):
            raise ValueError('Environment delivery requires one pinned systemd service unit.')
        if configuration.get('systemd_action') not in ('reload', 'restart'):
            raise ValueError('Unsupported systemd action.')
        for field in ('systemd_unit', 'systemd_action'):
            if configuration[field] != capabilities.get(field, ''):
                raise ValueError(f'Agent configuration exceeds the installed {field} capability.')
    pwd.getpwnam(configuration['app_user'])
    secure_root(configuration['delivery_root'])
    socket_path = Path(configuration['socket_path'])
    if not socket_path.is_absolute() or socket_path.name != 'agent.sock':
        raise ValueError('Invalid Agent socket path.')


def flatten_credential(data):
    account, asset = data['account'], data['asset']
    return {
        'key': data['key'], 'revision': data['revision'],
        'asset_id': asset['id'], 'asset': asset['name'], 'address': asset['address'],
        'account_id': account['id'], 'account': account['name'],
        'username': account['username'], 'secret_type': account['secret_type'],
        'secret': account['secret'],
    }


def render_environment(item):
    values = {
        'JMS_PAM_CREDENTIAL_KEY': item['key'],
        'JMS_PAM_CREDENTIAL_REVISION': item['revision'],
        'JMS_PAM_ASSET_ID': item['asset_id'],
        'JMS_PAM_ASSET_ADDRESS': item['address'],
        'JMS_PAM_ACCOUNT_ID': item['account_id'],
        'JMS_PAM_USERNAME': item['username'],
        'JMS_PAM_SECRET_TYPE': item['secret_type'],
        'JMS_PAM_SECRET': item['secret'],
    }
    lines = []
    for name, value in values.items():
        value = str(value)
        if any(char in value for char in ('\x00', '\r', '\n')):
            raise ValueError('EnvironmentFile values cannot contain NUL or newlines.')
        escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
        lines.append(f'{name}="{escaped}"')
    return '\n'.join(lines) + '\n'


class ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class Agent:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = read_json(config_file)
        self.capabilities = self.config['capabilities']
        self.configuration = self.config['configuration']
        validate_configuration(self.configuration, self.capabilities)
        self.remote = credential_client.CredentialClient(
            credential.Credential(self.config['agent_id'], self.config['agent_secret']),
            self.config.get('instance_id', self.config['agent_id']),
            client_profile.ClientProfile(
                endpoint=self.config['endpoint'], org_id=self.config['org_id'],
                source='jms-pam-agent',
            ),
        )
        self.state = read_json(self.config.get('state_file', STATE_FILE))
        self.credentials = read_json(self.config.get('credential_file', CREDENTIAL_FILE))
        self.delivered = read_json(self.delivery_file)
        self.authorized_keys = set(self.config.get('authorized_keys', self.configuration['credential_keys']))
        self.access_denied = bool(self.config.get('access_denied', False))
        self.lock = threading.Lock()

    @property
    def state_file(self):
        return self.config.get('state_file', STATE_FILE)

    @property
    def credential_file(self):
        return self.config.get('credential_file', CREDENTIAL_FILE)

    @property
    def delivery_file(self):
        default = str(Path(self.state_file).with_name('delivered.json'))
        return self.config.get('delivery_file', default)

    def save_config(self):
        atomic_write_json(self.config_file, self.config)

    def set_access_denied(self, denied, reason=''):
        with self.lock:
            if self.access_denied == denied and self.config.get('denied_reason', '') == reason:
                return
            self.access_denied = denied
            self.config['access_denied'] = denied
            self.config['denied_reason'] = reason
            self.save_config()

    def fetch(self, keys):
        fetched = {}
        revoked = set()
        for key in keys:
            try:
                response = self.remote.GetCredential(models.GetCredentialRequest(Key=key))._serialize()
                fetched[key] = flatten_credential(response)
            except (JumpServerPAMSDKException, OSError) as error:
                if identity_denied(error) or getattr(error, 'status_code', None) == 426:
                    raise
                code = response_error_code(error)
                if code in REVOKED_CODES:
                    revoked.add(key)
                print(
                    f'JumpServer PAM Agent: credential {key}: '
                    f'{code or type(error).__name__}',
                    file=sys.stderr,
                )
        if not fetched and not revoked:
            return set()
        with self.lock:
            if revoked:
                self.authorized_keys.difference_update(revoked)
                self.config['authorized_keys'] = sorted(self.authorized_keys)
                self.save_config()
            values = dict(self.credentials)
            changed = {
                key for key, item in fetched.items()
                if values.get(key, {}).get('revision') != item['revision']
            }
            values.update(fetched)
            if values != self.credentials:
                atomic_write_json(self.credential_file, values)
                self.credentials = values
        return changed

    def deliver(self, changed):
        if not changed:
            return
        mode = self.configuration['delivery_mode']
        if mode != 'socket':
            root = secure_root(self.configuration['delivery_root'])
            owner = self.configuration['app_user']
            for key in sorted(changed):
                with self.lock:
                    item = dict(self.credentials[key])
                suffix = 'json' if mode == 'json' else 'env'
                target = secure_target(root, f'{key}.{suffix}')
                content = (
                    json.dumps(item, ensure_ascii=False, indent=2) + '\n'
                    if mode == 'json' else render_environment(item)
                )
                atomic_write(target, content, owner=owner)
            if mode == 'environment':
                subprocess.run(
                    ['systemctl', self.configuration['systemd_action'], self.configuration['systemd_unit']],
                    check=True, stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
        with self.lock:
            delivered = dict(self.delivered)
            for key in changed:
                delivered[key] = {
                    'key': key, 'revision': self.credentials[key]['revision'],
                }
            atomic_write_json(self.delivery_file, delivered)
            self.delivered = delivered

    def sync(self):
        with self.lock:
            known = [
                models.KnownCredentialRevision(Key=key, Revision=item.get('revision', 0))
                for key, item in sorted(self.credentials.items())
            ]
            delivered = [
                models.KnownCredentialRevision(Key=key, Revision=item.get('revision', 0))
                for key, item in sorted(self.delivered.items()) if key in self.authorized_keys
            ]
        request = models.AgentSyncRequest(
            ConfigDigest=self.config.get('config_digest', ''), Credentials=known,
            DeliveredCredentials=delivered,
            SyncStatus=self.config.get('sync_status', ''),
            SyncError=self.config.get('sync_error', ''),
        )
        response = self.remote.SyncAgent(request)._serialize()
        metadata = {item['key']: item for item in response['credentials']}
        with self.lock:
            self.authorized_keys = set(metadata)
            self.config['authorized_keys'] = sorted(self.authorized_keys)
        configuration = response.get('configuration')
        try:
            if configuration is not None:
                validate_configuration(configuration, self.capabilities)
                self.configuration = configuration
                self.config['configuration'] = configuration
            keys = [
                key for key, item in metadata.items()
                if item['available'] and (
                    item['changed'] or self.credentials.get(key, {}).get('revision') != item['revision']
                )
            ]
            self.fetch(keys)
            pending = {
                key for key, item in metadata.items()
                if item['available']
                and self.credentials.get(key, {}).get('revision') == item['revision']
                and (
                    configuration is not None
                    or self.delivered.get(key, {}).get('revision') != item['revision']
                )
            }
            self.deliver(pending)
            self.config['config_digest'] = response['config_digest']
        except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError) as error:
            self.config['sync_status'] = 'error'
            self.config['sync_error'] = type(error).__name__
            self.save_config()
            raise
        self.config['sync_status'] = 'success'
        self.config['sync_error'] = ''
        self.set_access_denied(False)
        self.save_config()
        return response

    def confirm(self, key, revision):
        with self.lock:
            if self.access_denied:
                raise PermissionError(self.config.get('denied_reason') or 'Agent access is disabled.')
            if key not in self.authorized_keys:
                raise KeyError(f'Credential not authorized: {key}')
            item = self.credentials.get(key)
            if not item:
                raise KeyError(f'Credential not found: {key}')
            if type(revision) is not int or revision != item['revision']:
                raise ValueError('Confirm the exact revision used by the application.')
            state = dict(self.state)
            state[key] = {
                'key': key, 'revision': item['revision'], 'account_id': item['account_id'],
            }
            atomic_write_json(self.state_file, state)
            self.state = state
            return {**state[key], 'status': 'accepted'}

    def heartbeat(self):
        with self.lock:
            states = [
                models.CredentialState(
                    Key=item['key'], Revision=item['revision'], AccountId=item['account_id'],
                )
                for key, item in sorted(self.state.items()) if key in self.authorized_keys
            ]
        return self.remote.Heartbeat(models.HeartbeatRequest(Credentials=states))._serialize()

    def socket_reply(self, handler, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        handler.send_response(status)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('Content-Length', str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    def start_local_server(self):
        agent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/v1/health':
                    return agent.socket_reply(self, 200, {
                        'status': 'denied' if agent.access_denied else 'ok',
                        'sync_status': agent.config.get('sync_status', ''),
                    })
                prefix = '/v1/credentials/'
                if not self.path.startswith(prefix):
                    return agent.socket_reply(self, 404, {'code': 'not_found'})
                key = unquote(self.path[len(prefix):])
                with agent.lock:
                    if agent.access_denied:
                        return agent.socket_reply(self, 503, {
                            'code': agent.config.get('denied_reason') or 'agent_access_denied',
                        })
                    if key not in agent.authorized_keys:
                        return agent.socket_reply(self, 404, {'code': 'credential_not_authorized'})
                    item = agent.credentials.get(key)
                    if not item:
                        return agent.socket_reply(self, 404, {'code': 'credential_not_available'})
                    return agent.socket_reply(self, 200, item)

            def do_POST(self):
                if self.path != '/v1/confirm':
                    return agent.socket_reply(self, 404, {'code': 'not_found'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 4096:
                        raise ValueError('Invalid request size.')
                    data = json.loads(self.rfile.read(length))
                    result = agent.confirm(data['key'], data['revision'])
                    return agent.socket_reply(self, 200, result)
                except PermissionError as error:
                    return agent.socket_reply(self, 503, {'code': str(error)})
                except Exception as error:
                    return agent.socket_reply(self, 400, {'code': type(error).__name__})

            def log_message(self, *_):
                pass

        path = Path(self.capabilities['socket_path'])
        parent = path.parent
        secure_root(parent, 0o750)
        if path.is_symlink():
            raise ValueError('Agent socket path cannot be a symbolic link.')
        if path.exists():
            if not stat.S_ISSOCK(path.stat().st_mode):
                raise ValueError('Agent socket path is occupied by a non-socket file.')
            path.unlink()
        user = pwd.getpwnam(self.capabilities['app_user'])
        os.chown(parent, 0, user.pw_gid)
        os.chmod(parent, 0o750)
        server = ThreadingUnixHTTPServer(str(path), Handler)
        os.chown(path, user.pw_uid, user.pw_gid)
        os.chmod(path, 0o600)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server

    def run(self):
        server = self.start_local_server()
        stop = threading.Event()
        try:
            while True:
                denied = False
                try:
                    self.sync()
                except (JumpServerPAMSDKException, OSError) as error:
                    denied = identity_denied(error) or getattr(error, 'status_code', None) == 426
                    if denied:
                        self.set_access_denied(True, getattr(error, 'code', '') or 'agent_access_denied')
                    print(f'JumpServer PAM Agent: sync: {type(error).__name__}', file=sys.stderr)
                except (KeyError, TypeError, ValueError, subprocess.SubprocessError) as error:
                    print(f'JumpServer PAM Agent: apply: {type(error).__name__}', file=sys.stderr)
                try:
                    if not denied and not self.access_denied:
                        self.heartbeat()
                except (JumpServerPAMSDKException, OSError, KeyError, TypeError, ValueError) as error:
                    print(f'JumpServer PAM Agent: heartbeat: {type(error).__name__}', file=sys.stderr)
                stop.wait(self.config.get('poll_interval', 30))
        except KeyboardInterrupt:
            pass
        finally:
            server.shutdown()
            server.server_close()
            try:
                Path(self.capabilities['socket_path']).unlink()
            except FileNotFoundError:
                pass
            self.remote.close()


def register(args):
    configuration_id = str(uuid.UUID(args.configuration_id))
    base = Path(args.install_path) / configuration_id
    secure_root(base, 0o700)
    config_file = args.config or str(base / 'agent.json')
    if Path(config_file).is_symlink():
        raise ValueError('Agent configuration cannot be a symbolic link.')
    config_path = Path(config_file).resolve(strict=False)
    if not config_path.is_relative_to(base.resolve()) or config_path == base.resolve():
        raise ValueError('Agent configuration must remain inside its installation directory.')
    config_file = str(config_path)
    existing = read_json(config_file)
    if existing:
        agent = Agent(config_file)
        try:
            agent.sync()
        finally:
            agent.remote.close()
        print('Existing Agent identity verified and reused; registration token was not submitted.')
        return config_file

    pwd.getpwnam(args.app_user)
    response = requests.post(
        f"{args.endpoint.rstrip('/')}{CLIENT_PATH}/register-agent/",
        json={
            'token': args.token, 'instance_id': args.instance_id,
            'name': args.name or args.instance_id,
            'client_version': __version__, 'protocol_version': PROTOCOL_VERSION,
            'config_schema_version': CONFIG_SCHEMA_VERSION,
        },
        timeout=10,
    )
    try:
        response.raise_for_status()
        identity = response.json()
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError('Agent registration failed; the local configuration was not replaced.') from error
    configuration = identity['configuration']
    if identity['configuration_id'] != configuration_id:
        raise ValueError('Registration token belongs to another access configuration.')
    if configuration['app_user'] != args.app_user:
        raise ValueError('Application user does not match the server configuration.')
    expected_root = str(Path(args.install_path) / 'credentials' / configuration_id)
    if configuration['delivery_root'] != expected_root:
        raise ValueError('Install path does not match the server configuration.')
    capabilities = {
        key: configuration.get(key, '') for key in (
            'delivery_root', 'socket_path', 'app_user', 'systemd_unit', 'systemd_action',
        )
    }
    validate_configuration(configuration, capabilities)
    secure_root(configuration['delivery_root'])
    config = {
        'endpoint': args.endpoint.rstrip('/'), 'org_id': identity['org_id'],
        'agent_id': identity['agent_id'], 'agent_secret': identity['agent_secret'],
        'configuration_id': identity['configuration_id'], 'instance_id': args.instance_id,
        'configuration': configuration, 'capabilities': capabilities,
        'config_digest': identity['config_digest'],
        'authorized_keys': configuration['credential_keys'],
        'credential_file': str(base / 'credentials.json'),
        'delivery_file': str(base / 'delivered.json'),
        'state_file': str(base / 'state.json'), 'poll_interval': 30,
        'sync_status': '', 'sync_error': '', 'access_denied': False,
    }
    atomic_write_json(config_file, config)
    atomic_write_json(config['credential_file'], {})
    atomic_write_json(config['delivery_file'], {})
    atomic_write_json(config['state_file'], {})
    return config_file


def install(args):
    config_file = register(args)
    executable = shutil.which('jms-pam-agent')
    command = [executable] if executable else [sys.executable, '-m', 'jms_pam.agent']
    command.extend(('run', '--config', config_file))
    service = f'jms-pam-agent-{uuid.UUID(args.configuration_id)}.service'
    unit_path = Path('/etc/systemd/system') / service
    unit = (
        '[Unit]\nDescription=JumpServer PAM Agent\nAfter=network-online.target\n\n'
        '[Service]\nType=simple\nUser=root\n'
        f'ExecStart={" ".join(shlex.quote(value) for value in command)}\n'
        'Restart=always\nRestartSec=5\n\n'
        '[Install]\nWantedBy=multi-user.target\n'
    )
    atomic_write(unit_path, unit, mode=0o644)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', service], check=True)
    subprocess.run(['systemctl', 'is-active', '--quiet', service], check=True)


def confirm_local(args):
    body = json.dumps({'key': args.key, 'revision': args.revision}).encode()
    request = (
        b'POST /v1/confirm HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n'
        + f'Content-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode() + body
    )
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(args.socket)
        client.sendall(request)
        response = b''
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            response += chunk
    status_line, _, payload = response.partition(b'\r\n\r\n')
    if b' 200 ' not in status_line.split(b'\r\n', 1)[0]:
        raise RuntimeError(payload.decode(errors='replace'))
    print(payload.decode())


def build_parser():
    parser = argparse.ArgumentParser(prog='jms-pam-agent')
    commands = parser.add_subparsers(dest='command', required=True)

    def add_registration_arguments(command):
        command.add_argument('--endpoint', required=True)
        command.add_argument('--token', required=True)
        command.add_argument('--instance-id', required=True)
        command.add_argument('--configuration-id', required=True)
        command.add_argument('--app-user', required=True)
        command.add_argument('--install-path', required=True)
        command.add_argument('--name')
        command.add_argument('--config', default='')

    register_parser = commands.add_parser('register')
    add_registration_arguments(register_parser)
    register_parser.set_defaults(handler=register)

    install_parser = commands.add_parser('install')
    add_registration_arguments(install_parser)
    install_parser.set_defaults(handler=install)

    run_parser = commands.add_parser('run')
    run_parser.add_argument('--config', default=CONFIG_FILE)
    run_parser.set_defaults(handler=lambda args: Agent(args.config).run())

    confirm_parser = commands.add_parser('confirm')
    confirm_parser.add_argument('key')
    confirm_parser.add_argument('--revision', type=int, required=True)
    confirm_parser.add_argument('--socket', required=True)
    confirm_parser.set_defaults(handler=confirm_local)
    return parser


def main():
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
