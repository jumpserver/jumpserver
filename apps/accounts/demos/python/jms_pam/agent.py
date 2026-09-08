import argparse
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import requests

from .main import CLIENT_PATH, CredentialAPIClient
from .events import EventWorker, DeliveryError

CONFIG_FILE = '/etc/jumpserver-pam/agent.json'
STATE_FILE = '/var/lib/jumpserver-pam/state.json'
CREDENTIAL_FILE = '/etc/jumpserver-pam/credentials.json'


def read_json(path, default=None):
    try:
        with open(path, encoding='utf-8') as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {} if default is None else default


def atomic_write_json(path, data, mode=0o600, owner=None):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', dir=target.parent,
        prefix=f'.{target.name}.', delete=False,
    ) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        temporary = stream.name
    os.chmod(temporary, mode)
    if owner:
        user = pwd.getpwnam(owner)
        os.chown(temporary, user.pw_uid, user.pw_gid)
    os.replace(temporary, target)


class Agent:
    def __init__(self, config_file=CONFIG_FILE):
        self.config = read_json(config_file)
        self.remote = CredentialAPIClient(
            self.config['endpoint'],
            self.config['agent_id'],
            self.config['agent_secret'],
            self.config['org_id'],
            source='jms-pam-agent',
            instance_id=self.config.get('instance_id', self.config['agent_id']),
        )
        self.state = read_json(self.config.get('state_file', STATE_FILE))
        self.credentials = read_json(self.config.get('credential_file', CREDENTIAL_FILE))
        self.lock = threading.Lock()
        self.events = None
        self.notification_session = requests.Session()
        self.notification_session.trust_env = False

    @property
    def credential_file(self):
        return self.config.get('credential_file', CREDENTIAL_FILE)

    @property
    def state_file(self):
        return self.config.get('state_file', STATE_FILE)

    def poll(self, keys=None, remote=None):
        fetched = {key: (remote or self.remote).get_credential(key)
                   for key in keys or self.config['credential_keys']}
        changed = False
        with self.lock:
            credentials = dict(self.credentials)
            for key, data in fetched.items():
                current = credentials.get(key, {})
                if current.get('revision', 0) >= data['revision']:
                    continue
                account = data['account']
                asset = data['asset']
                credentials[key] = {
                    'key': key,
                    'revision': data['revision'],
                    'asset_id': asset['id'],
                    'asset': asset['name'],
                    'address': asset['address'],
                    'account_id': account['id'],
                    'account': account['name'],
                    'username': account['username'],
                    'secret_type': account['secret_type'],
                    'secret': account['secret'],
                }
                changed = True
            if changed:
                atomic_write_json(
                    self.credential_file,
                    credentials,
                    owner=self.config.get('app_user'),
                )
                self.credentials = credentials
        return changed

    def confirm(self, key, revision):
        with self.lock:
            item = self.credentials.get(key)
            if not item:
                raise KeyError(f'Credential not found: {key}')
            if type(revision) is not int or revision != item['revision']:
                raise ValueError('Confirm the exact revision actually used by your application')
            applied = {
                'key': key,
                'revision': item['revision'],
                'account_id': item['account_id'],
            }
            self.remote.confirm(applied)
            state = dict(self.state)
            state[key] = applied
            atomic_write_json(self.state_file, state)
            self.state = state
        return applied

    def heartbeat(self):
        with self.lock:
            states = list(self.state.values())
        return self.remote.heartbeat(states)

    def run(self):
        server = self.start_local_server()
        if self.config.get('notification_enabled'):
            remote = self.remote.fork()
            self.events = EventWorker(remote, lambda event: self.notify(event, remote))
            self.events.start()
        stop = threading.Event()
        try:
            while True:
                try:
                    self.poll()
                    self.heartbeat()
                except requests.RequestException as error:
                    print(f'JumpServer PAM Agent: {error}', file=sys.stderr)
                stop.wait(self.config.get('poll_interval', 30))
        except KeyboardInterrupt:
            pass
        finally:
            if self.events:
                self.events.close()
            server.shutdown()
            self.remote.session.close()
            self.notification_session.close()

    def notify(self, event, remote):
        url = self.config.get('notification_url', '')
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise DeliveryError('http_failed')
        if event['event'] == 'credential.published':
            try:
                self.poll(keys=[event['key']], remote=remote)
                with self.lock:
                    current = self.credentials.get(event['key'], {})
                    if current.get('revision') != event['revision']:
                        raise DeliveryError('credential_not_ready')
            except (requests.RequestException, OSError):
                raise DeliveryError('credential_not_ready') from None
        try:
            response = self.notification_session.post(url, json=event, timeout=10, allow_redirects=False)
            status_code = response.status_code
            response.close()
        except requests.RequestException:
            raise DeliveryError('http_failed') from None
        if not 200 <= status_code < 300:
            raise DeliveryError('http_failed', status_code)
        return status_code

    def start_local_server(self):
        agent = self

        class Handler(BaseHTTPRequestHandler):
            def reply(self, code, data):
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path != '/v1/health':
                    return self.reply(404, {'detail': 'Not found'})
                return self.reply(200, {'status': 'ok'})

            def do_POST(self):
                if self.path != '/v1/confirm':
                    return self.reply(404, {'detail': 'Not found'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 4096:
                        raise ValueError('Invalid request size')
                    data = json.loads(self.rfile.read(length) or b'{}')
                    return self.reply(200, agent.confirm(data['key'], data['revision']))
                except Exception as error:
                    return self.reply(400, {'detail': str(error)})

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', self.config.get('port', 8081)), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server


def register(args):
    response = requests.post(
        f"{args.endpoint.rstrip('/')}{CLIENT_PATH}/register-agent/",
        json={
            'token': args.token,
            'instance_id': args.instance_id,
            'name': args.name or args.instance_id,
        },
        timeout=10,
    )
    response.raise_for_status()
    identity = response.json()
    config = {
        'endpoint': args.endpoint.rstrip('/'),
        'org_id': identity['org_id'],
        'agent_id': identity['agent_id'],
        'agent_secret': identity['agent_secret'],
        'credential_keys': identity['credential_keys'],
        'configuration_id': identity['configuration_id'],
        'instance_id': args.instance_id,
        'credential_file': args.credential_file,
        'state_file': args.state_file,
        'app_user': args.app_user,
        'poll_interval': 30,
        'port': args.port,
        'notification_enabled': identity.get('notification_enabled', False),
        'notification_url': identity.get('notification_url', ''),
    }
    atomic_write_json(args.config, config)
    if not os.path.exists(args.credential_file):
        atomic_write_json(args.credential_file, {}, owner=args.app_user)
    atomic_write_json(args.state_file, {})
    return config


def install(args):
    register(args)
    executable = shutil.which('jms-pam-agent') or f'{sys.executable} -m jms_pam.agent'
    unit = (
        '[Unit]\nDescription=JumpServer PAM Agent\nAfter=network-online.target\n\n'
        '[Service]\nType=simple\nUser=root\n'
        f'ExecStart={executable} run --config {args.config}\n'
        'Restart=always\nRestartSec=5\n\n'
        '[Install]\nWantedBy=multi-user.target\n'
    )
    Path('/etc/systemd/system/jms-pam-agent.service').write_text(unit, encoding='utf-8')
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'jms-pam-agent'], check=True)


def confirm_local(args):
    response = requests.post(
        f'http://127.0.0.1:{args.port}/v1/confirm',
        json={'key': args.key, 'revision': args.revision}, timeout=10,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False))


def build_parser():
    parser = argparse.ArgumentParser(prog='jms-pam-agent')
    commands = parser.add_subparsers(dest='command', required=True)

    def add_registration_arguments(command):
        command.add_argument('--endpoint', required=True)
        command.add_argument('--token', required=True)
        command.add_argument('--instance-id', required=True)
        command.add_argument('--credential', action='append', required=True)
        command.add_argument('--app-user', required=True)
        command.add_argument('--name')
        command.add_argument('--config', default=CONFIG_FILE)
        command.add_argument('--credential-file', default=CREDENTIAL_FILE)
        command.add_argument('--state-file', default=STATE_FILE)
        command.add_argument('--port', type=int, default=8081)

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
    confirm_parser.add_argument('--port', type=int, default=8081)
    confirm_parser.set_defaults(handler=confirm_local)
    return parser


def main():
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
