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

import requests

from .main import CLIENT_PATH, SignedClient

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


class AgentRemoteClient(SignedClient):
    def __init__(self, config):
        super().__init__(
            config['endpoint'], config['agent_id'], config['agent_secret'],
            config['org_id'], source='jms-pam-agent',
        )

    def get_credential(self, key):
        return self.request('GET', f'{CLIENT_PATH}/credential/', params={'key': key})

    def confirm(self, item):
        return self.request('POST', f'{CLIENT_PATH}/confirm/', data={
            'key': item['key'],
            'revision': item['revision'],
            'account_id': item['account_id'],
        })

    def heartbeat(self, credentials):
        return self.request('POST', f'{CLIENT_PATH}/heartbeat/', data={
            'credentials': credentials,
        })


class Agent:
    def __init__(self, config_file=CONFIG_FILE):
        self.config = read_json(config_file)
        self.remote = AgentRemoteClient(self.config)
        self.state = read_json(self.config.get('state_file', STATE_FILE))
        self.credentials = read_json(self.config.get('credential_file', CREDENTIAL_FILE))
        self.lock = threading.Lock()

    @property
    def credential_file(self):
        return self.config.get('credential_file', CREDENTIAL_FILE)

    @property
    def state_file(self):
        return self.config.get('state_file', STATE_FILE)

    def poll(self):
        changed = False
        with self.lock:
            for key in self.config['credential_keys']:
                data = self.remote.get_credential(key)
                current = self.credentials.get(key, {})
                if current.get('revision') == data['revision']:
                    continue
                account = data['account']
                asset = data['asset']
                self.credentials[key] = {
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
                    self.credentials,
                    owner=self.config.get('app_user'),
                )
        return changed

    def confirm(self, key):
        with self.lock:
            item = self.credentials.get(key)
            if not item:
                raise KeyError(f'Credential not found: {key}')
            applied = {
                'key': key,
                'revision': item['revision'],
                'account_id': item['account_id'],
            }
            self.remote.confirm(applied)
            self.state[key] = applied
            atomic_write_json(self.state_file, self.state)
        return applied

    def heartbeat(self):
        with self.lock:
            states = list(self.state.values())
        return self.remote.heartbeat(states)

    def run(self):
        server = self.start_local_server()
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
            server.shutdown()
            self.remote.session.close()

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
                    data = json.loads(self.rfile.read(length) or b'{}')
                    return self.reply(200, agent.confirm(data['key']))
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
        'credential_keys': args.credential,
        'credential_file': args.credential_file,
        'state_file': args.state_file,
        'app_user': args.app_user,
        'poll_interval': 30,
        'port': args.port,
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
        json={'key': args.key}, timeout=10,
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
    confirm_parser.add_argument('--port', type=int, default=8081)
    confirm_parser.set_defaults(handler=confirm_local)
    return parser


def main():
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == '__main__':
    main()
