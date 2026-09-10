import argparse
import hashlib
import json
import os
import pwd
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import requests

from .main import CLIENT_PATH, CredentialAPIClient, REVOKED_CODES, response_error_code, identity_denied
from .events import EventWorker, DeliveryError

CONFIG_FILE = '/etc/jumpserver-pam/agent.json'
STATE_FILE = '/var/lib/jumpserver-pam/state.json'
DELIVERY_STATE_FILE = '/var/lib/jumpserver-pam/delivery-state.json'
CREDENTIAL_FILE = '/etc/jumpserver-pam/credentials.json'
DELIVERY_FIELDS = {
    'key', 'revision', 'asset_id', 'address', 'account_id',
    'username', 'secret_type', 'secret',
}
ENV_NAME = re.compile(r'^[A-Z_][A-Z0-9_]*$')


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


def atomic_write_text(path, data, mode=0o600, owner=None):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.is_symlink():
        raise ValueError('Delivery path cannot be a symbolic link.')
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', dir=target.parent,
        prefix=f'.{target.name}.', delete=False,
    ) as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = stream.name
    try:
        os.chmod(temporary, mode)
        if owner:
            user = pwd.getpwnam(owner)
            os.chown(temporary, user.pw_uid, user.pw_gid)
        if target.exists() and target.is_symlink():
            raise ValueError('Delivery path cannot be a symbolic link.')
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parse_mode(value):
    mode = int(value, 8) if isinstance(value, str) else value
    if type(mode) is not int or mode < 0 or mode > 0o777 or mode & 0o077:
        raise ValueError('Delivery mode must not grant access to group or others.')
    return mode


def validate_delivery_path(path):
    target = Path(path)
    for component in (target, *target.parents):
        if component.is_symlink():
            raise ValueError('Delivery path must not contain symbolic links.')
    parent = target.parent
    while not parent.exists():
        parent = parent.parent
    info = parent.stat()
    if info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Delivery path must be under a root-owned directory not writable by group or others.')


def validate_hook(command):
    if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
        raise ValueError('Delivery apply hook must be a non-empty argument list.')
    executable = Path(command[0])
    if not executable.is_absolute() or executable.is_symlink():
        raise ValueError('Delivery apply hook must be an absolute, non-symlink path.')
    info = executable.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise ValueError('Delivery apply hook must be a root-owned regular file and not group/world writable.')
    if not os.access(executable, os.X_OK):
        raise ValueError('Delivery apply hook must be executable.')


def validate_deliveries(config):
    deliveries = config.get('deliveries', {})
    if not isinstance(deliveries, dict):
        raise ValueError('Agent deliveries must be an object.')
    for key, rule in deliveries.items():
        if key not in config['credential_keys'] or not isinstance(rule, dict):
            raise ValueError('Each delivery must reference a selected credential.')
        if rule.get('format', 'env') != 'env':
            raise ValueError('Only env credential delivery is supported.')
        path = Path(rule.get('path', ''))
        if not path.is_absolute() or path == Path('/') or '\x00' in str(path):
            raise ValueError('Delivery path must be an absolute file path.')
        validate_delivery_path(path)
        fields = rule.get('fields')
        if not isinstance(fields, dict) or not fields:
            raise ValueError('Delivery fields must be a non-empty object.')
        for name, source in fields.items():
            if not ENV_NAME.fullmatch(name) or source not in DELIVERY_FIELDS:
                raise ValueError('Delivery fields contain an unsupported name or credential field.')
        pwd.getpwnam(rule.get('owner', config.get('app_user', '')))
        parse_mode(rule.get('mode', '0600'))
        confirmation = rule.get('confirmation', 'manual')
        if confirmation not in ('manual', 'apply'):
            raise ValueError('Delivery confirmation must be manual or apply.')
        command = rule.get('apply')
        if command:
            validate_hook(command)
        elif confirmation == 'apply':
            raise ValueError('Automatic confirmation requires a delivery apply hook.')
        timeout = rule.get('timeout', 60)
        if type(timeout) is not int or not 1 <= timeout <= 3600:
            raise ValueError('Delivery hook timeout must be between 1 and 3600 seconds.')


def delivery_fingerprint(rule):
    data = {key: rule.get(key) for key in (
        'format', 'path', 'fields', 'owner', 'mode', 'apply', 'confirmation', 'timeout',
    )}
    encoded = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def render_env(rule, credential):
    values = []
    for name, source in rule['fields'].items():
        value = str(credential[source])
        if any(char in value for char in ('\x00', '\r', '\n')):
            raise ValueError('Env delivery does not support NUL or newline characters.')
        values.append(f'{name}={shlex.quote(value)}')
    return '\n'.join(values) + '\n'


def run_hook(rule, event, key, revision):
    command = rule.get('apply')
    if not command:
        return
    validate_hook(command)
    environment = {
        'PATH': '/usr/sbin:/usr/bin:/sbin:/bin',
        'JMS_PAM_EVENT': event,
        'JMS_PAM_CREDENTIAL_KEY': key,
        'JMS_PAM_REVISION': str(revision or ''),
        'JMS_PAM_CREDENTIAL_FILE': rule['path'],
    }
    result = subprocess.run(
        command, shell=False, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=rule.get('timeout', 60), check=False,
    )
    if result.returncode:
        raise RuntimeError(f'Delivery apply hook exited with status {result.returncode}.')


class Agent:
    def __init__(self, config_file=CONFIG_FILE):
        self.config = read_json(config_file)
        validate_deliveries(self.config)
        self.remote = CredentialAPIClient(
            self.config['endpoint'],
            self.config['agent_id'],
            self.config['agent_secret'],
            self.config['org_id'],
            source='jms-pam-agent',
            instance_id=self.config.get('instance_id', self.config['agent_id']),
        )
        self.state = read_json(self.config.get('state_file', STATE_FILE))
        self.delivery_state = read_json(self.config.get('delivery_state_file', DELIVERY_STATE_FILE))
        self.credentials = read_json(self.config.get('credential_file', CREDENTIAL_FILE))
        self.lock = threading.Lock()
        # ponytail: credential changes are rare; use per-key locks only if hook throughput becomes measurable.
        self.delivery_lock = threading.Lock()
        self.events = None
        self.notification_session = requests.Session()
        self.notification_session.trust_env = False

    @property
    def credential_file(self):
        return self.config.get('credential_file', CREDENTIAL_FILE)

    @property
    def state_file(self):
        return self.config.get('state_file', STATE_FILE)

    @property
    def delivery_state_file(self):
        return self.config.get('delivery_state_file', DELIVERY_STATE_FILE)

    @property
    def deliveries(self):
        return self.config.get('deliveries', {})

    def save_delivery_state(self, key, value, expected=None):
        with self.lock:
            if expected is not None and self.delivery_state.get(key) != expected:
                return False
            states = dict(self.delivery_state)
            states[key] = value
            atomic_write_json(self.delivery_state_file, states)
            self.delivery_state = states
            return True

    def stage_revocations(self, removed):
        if not removed or not self.deliveries:
            return
        states = dict(self.delivery_state)
        for key, credential in removed.items():
            rule = self.deliveries.get(key)
            if not rule:
                continue
            states[key] = {
                'action': 'revoke', 'status': 'pending',
                'revision': credential.get('revision', 0),
                'account_id': credential.get('account_id'),
                'rule_fingerprint': delivery_fingerprint(rule), 'error': '',
            }
        if states != self.delivery_state:
            atomic_write_json(self.delivery_state_file, states)
            self.delivery_state = states

    def poll(self, keys=None, remote=None):
        fetched, revoked, errors = {}, set(), {}
        with self.lock:
            sent_credentials, sent_state = dict(self.credentials), dict(self.state)
        for key in self.config['credential_keys'] if keys is None else keys:
            try:
                fetched[key] = (remote or self.remote).get_credential(key)
            except requests.RequestException as exc:
                if identity_denied(exc):
                    raise
                code = response_error_code(exc)
                if code in REVOKED_CODES:
                    revoked.add(key)
                errors[key] = code if code in REVOKED_CODES or code == 'credential_changing' else type(exc).__name__
                # Never print response bodies, credentials or authentication headers.
                print(f'JumpServer PAM Agent: credential {key}: {errors[key]}', file=sys.stderr)
        changed = False
        with self.lock:
            self.remove_revoked(revoked, sent_credentials, sent_state)
            credentials = dict(self.credentials)
            delivery_states = dict(getattr(self, 'delivery_state', {}))
            for key, data in fetched.items():
                if self.credentials.get(key) is not sent_credentials.get(key):
                    continue
                current = credentials.get(key, {})
                if current.get('revision', 0) > data['revision']:
                    continue
                if current.get('revision') == data['revision']:
                    # Remember a fresh successful fetch, even when no file write is needed.
                    credentials[key] = dict(current)
                else:
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
                credential = credentials.get(key)
                rule = self.deliveries.get(key)
                if credential and rule and delivery_states.get(key, {}).get('action') == 'revoke':
                    delivery_states[key] = {
                        'action': 'publish', 'status': 'pending',
                        'revision': credential['revision'],
                        'account_id': credential['account_id'],
                        'rule_fingerprint': delivery_fingerprint(rule), 'error': '',
                    }
            if changed:
                atomic_write_json(
                    self.credential_file,
                    credentials,
                    owner=self.config.get('app_user'),
                )
            if delivery_states != getattr(self, 'delivery_state', {}):
                atomic_write_json(self.delivery_state_file, delivery_states)
                self.delivery_state = delivery_states
            self.credentials = credentials
        self.reconcile_deliveries(keys)
        return errors

    def remove_revoked(self, keys, sent_credentials, sent_state):
        # Caller holds self.lock. A late response must not remove a newer fetch/confirmation.
        credentials, state = dict(self.credentials), dict(self.state)
        removed = {}
        for key in keys:
            if (self.credentials.get(key) is sent_credentials.get(key)
                    and self.state.get(key) is sent_state.get(key)):
                credential = credentials.pop(key, None)
                if credential:
                    removed[key] = credential
                state.pop(key, None)
        self.stage_revocations(removed)
        if credentials != self.credentials:
            atomic_write_json(self.credential_file, credentials, owner=self.config.get('app_user'))
            self.credentials = credentials
        if state != self.state:
            atomic_write_json(self.state_file, state)
            self.state = state

    def deliver(self, key):
        rule = self.deliveries.get(key)
        if not rule:
            return
        with self.delivery_lock:
            with self.lock:
                credential = dict(self.credentials.get(key, {}))
                delivered = dict(self.delivery_state.get(key, {}))
                confirmed = dict(self.state.get(key, {}))
            if not credential:
                return
            fingerprint = delivery_fingerprint(rule)
            current = (
                delivered.get('action') == 'publish'
                and delivered.get('status') == 'applied'
                and delivered.get('revision') == credential['revision']
                and delivered.get('account_id') == credential['account_id']
                and delivered.get('rule_fingerprint') == fingerprint
                and Path(rule['path']).is_file()
                and not Path(rule['path']).is_symlink()
            )
            if not current:
                delivered = {
                    'action': 'publish', 'status': 'pending',
                    'revision': credential['revision'],
                    'account_id': credential['account_id'],
                    'rule_fingerprint': fingerprint, 'error': '',
                }
                self.save_delivery_state(key, delivered)
                try:
                    atomic_write_text(
                        rule['path'], render_env(rule, credential),
                        parse_mode(rule.get('mode', '0600')),
                        rule.get('owner', self.config.get('app_user')),
                    )
                    run_hook(rule, 'published', key, credential['revision'])
                    with self.lock:
                        latest = self.credentials.get(key)
                        still_current = (
                            latest and latest.get('revision') == credential['revision']
                            and latest.get('account_id') == credential['account_id']
                            and self.delivery_state.get(key, {}).get('action') == 'publish'
                        )
                    if not still_current:
                        return
                    applied = {**delivered, 'status': 'applied'}
                    if not self.save_delivery_state(key, applied, expected=delivered):
                        return
                    delivered = applied
                except Exception as exc:
                    pending = {**delivered, 'error': type(exc).__name__}
                    self.save_delivery_state(key, pending, expected=delivered)
                    print(
                        f'JumpServer PAM Agent: delivery {key}: {pending["error"]}',
                        file=sys.stderr,
                    )
                    return
            if (
                rule.get('confirmation', 'manual') == 'apply'
                and confirmed.get('revision', 0) < credential['revision']
            ):
                try:
                    self.confirm(key, credential['revision'])
                except (requests.RequestException, OSError, KeyError, ValueError) as exc:
                    print(
                        f'JumpServer PAM Agent: delivery confirmation {key}: {type(exc).__name__}',
                        file=sys.stderr,
                    )

    def revoke_delivery(self, key):
        rule = self.deliveries.get(key)
        if not rule:
            return
        with self.delivery_lock:
            with self.lock:
                delivery = dict(self.delivery_state.get(key, {}))
                if delivery.get('action') == 'revoke' and delivery.get('status') != 'applied':
                    credentials, state = dict(self.credentials), dict(self.state)
                    credentials.pop(key, None)
                    state.pop(key, None)
                    if credentials != self.credentials:
                        atomic_write_json(
                            self.credential_file, credentials,
                            owner=self.config.get('app_user'),
                        )
                        self.credentials = credentials
                    if state != self.state:
                        atomic_write_json(self.state_file, state)
                        self.state = state
            if delivery.get('action') != 'revoke' or delivery.get('status') == 'applied':
                return
            try:
                target = Path(rule['path'])
                if target.exists() or target.is_symlink():
                    target.unlink()
                run_hook(rule, 'revoked', key, delivery.get('revision'))
                updated = {**delivery, 'status': 'applied', 'error': ''}
            except Exception as exc:
                updated = {**delivery, 'status': 'pending', 'error': type(exc).__name__}
                print(
                    f'JumpServer PAM Agent: delivery revoke {key}: {updated["error"]}',
                    file=sys.stderr,
                )
            self.save_delivery_state(key, updated, expected=delivery)

    def reconcile_deliveries(self, keys=None):
        if not self.deliveries:
            return
        candidates = set(self.deliveries if keys is None else keys)
        with self.lock:
            candidates.update(
                key for key, value in self.delivery_state.items()
                if value.get('action') == 'revoke' and value.get('status') != 'applied'
            )
        for key in candidates:
            with self.lock:
                revoked = self.delivery_state.get(key, {}).get('action') == 'revoke'
                credential_exists = key in self.credentials
            try:
                if revoked:
                    self.revoke_delivery(key)
                elif credential_exists:
                    self.deliver(key)
            except Exception as exc:
                print(f'JumpServer PAM Agent: delivery {key}: {type(exc).__name__}', file=sys.stderr)

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
            sent_state, sent_credentials = dict(self.state), dict(self.credentials)
        result = self.remote.heartbeat(list(sent_state.values()))
        revoked = {error['key'] for error in result.get('errors', []) if error['code'] in REVOKED_CODES}
        with self.lock:
            self.remove_revoked(revoked, sent_credentials, sent_state)
        self.reconcile_deliveries(revoked)
        return result

    def run(self):
        server = self.start_local_server()
        if self.config.get('notification_enabled'):
            remote = self.remote.fork()
            self.events = EventWorker(remote, lambda event: self.notify(event, remote))
            self.events.start()
        stop = threading.Event()
        try:
            while True:
                denied = False
                try:
                    self.poll()
                except (requests.RequestException, OSError) as error:
                    denied = identity_denied(error)
                    print(f'JumpServer PAM Agent: poll: {type(error).__name__}', file=sys.stderr)
                self.reconcile_deliveries()
                try:
                    if not denied:
                        self.heartbeat()
                except (requests.RequestException, OSError) as error:
                    print(f'JumpServer PAM Agent: heartbeat: {type(error).__name__}', file=sys.stderr)
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
                errors = self.poll(keys=[event['key']], remote=remote)
                if errors and event['key'] in errors:
                    raise DeliveryError('credential_not_ready')
                with self.lock:
                    current = self.credentials.get(event['key'], {})
                    if current.get('revision') != event['revision']:
                        raise DeliveryError('credential_not_ready')
                    delivery = getattr(self, 'delivery_state', {}).get(event['key'], {})
                    rule = self.deliveries.get(event['key'], {})
                    if rule.get('confirmation') == 'apply' and (
                        delivery.get('status') != 'applied'
                        or delivery.get('revision') != event['revision']
                    ):
                        raise DeliveryError('application_apply_failed')
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
    existing = read_json(args.config)
    if existing:
        if (existing.get('endpoint', '').rstrip('/') != args.endpoint.rstrip('/')
                or existing.get('instance_id') != args.instance_id
                or existing.get('credential_file') != args.credential_file
                or existing.get('state_file') != args.state_file
                or existing.get('app_user') != args.app_user
                or existing.get('port') != args.port):
            raise ValueError('Existing Agent configuration does not match this installation. '
                             'Use the original parameters or a separate configuration path.')
        agent = Agent(args.config)
        try:
            agent.heartbeat()
        except requests.RequestException as exc:
            raise RuntimeError('Existing Agent identity could not be verified. Configuration was preserved; '
                               'check connectivity and whether the instance/configuration is enabled. '
                               'Registration will not replace it.') from exc
        finally:
            agent.remote.session.close()
            agent.notification_session.close()
        print('Existing Agent identity verified and reused; registration token was not submitted.')
        return existing

    # Validate local requirements before consuming the one-time token.
    pwd.getpwnam(args.app_user)
    if read_json(args.credential_file) or read_json(args.state_file):
        raise ValueError('Credential/state files exist without an Agent identity. Restore the original '
                         'configuration or choose separate paths; existing files were preserved.')
    for path in (args.config, args.credential_file, args.state_file):
        parent = Path(path).parent
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=parent):
            pass
    try:
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
    except requests.RequestException as exc:
        raise RuntimeError('Registration failed. Check whether the instance was created before retrying. '
                           'If its local identity was lost, review/remove the unused instance or use a '
                           'different instance ID and a new token; do not overwrite an active instance.') from exc
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
    try:
        atomic_write_json(args.config, config)
    except OSError as exc:
        raise RuntimeError('Agent was registered, but its identity could not be saved. Fix local storage, '
                           'then review/remove the unused instance or use a new instance ID and token. '
                           'Do not overwrite an active instance.') from exc
    if not os.path.exists(args.credential_file):
        atomic_write_json(args.credential_file, {}, owner=args.app_user)
    if not os.path.exists(args.state_file):
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
    subprocess.run(['systemctl', 'enable', 'jms-pam-agent'], check=True)
    subprocess.run(['systemctl', 'restart', 'jms-pam-agent'], check=True)
    subprocess.run(['systemctl', 'is-active', '--quiet', 'jms-pam-agent'], check=True)


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
