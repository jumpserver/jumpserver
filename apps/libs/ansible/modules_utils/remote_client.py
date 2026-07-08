import os
import re
import signal
import sys
import time
import traceback
from functools import wraps

import paramiko
from sshtunnel import SSHTunnelForwarder

DEFAULT_RE = '.*'
SU_PROMPT_LOCALIZATIONS = [
    'Password', '암호', 'パスワード', 'Adgangskode', 'Contraseña', 'Contrasenya',
    'Hasło', 'Heslo', 'Jelszó', 'Lösenord', 'Mật khẩu', 'Mot de passe',
    'Parola', 'Parool', 'Pasahitza', 'Passord', 'Passwort', 'Salasana',
    'Sandi', 'Senha', 'Wachtwoord', 'ססמה', 'Лозинка', 'Парола', 'Пароль',
    'गुप्तशब्द', 'शब्दकूट', 'సంకేతపదము', 'හස්පදය', '密码', '密碼', '口令',
]


def get_become_prompt_re():
    pattern_segments = (r'(\w+\'s )?' + p for p in SU_PROMPT_LOCALIZATIONS)
    prompt_pattern = "|".join(pattern_segments) + r' ?(:|：) ?'
    return re.compile(prompt_pattern, flags=re.IGNORECASE)


become_prompt_re = get_become_prompt_re()


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=22),
        login_user=dict(type='str', required=False, default='root'),
        login_password=dict(type='str', required=False, no_log=True),
        login_secret_type=dict(type='str', required=False, default='password'),
        login_private_key_path=dict(type='str', required=False, no_log=True),
        gateway_args=dict(type='str', required=False, default=''),
        recv_timeout=dict(type='int', required=False, default=30),
        delay_time=dict(type='int', required=False, default=2),
        prompt=dict(type='str', required=False, default='.*'),
        answers=dict(type='str', required=False, default='.*'),
        commands=dict(type='raw', required=False),

        become=dict(type='bool', default=False, required=False),
        become_method=dict(type='str', required=False),
        become_user=dict(type='str', required=False),
        become_password=dict(type='str', required=False, no_log=True),
        become_private_key_path=dict(type='str', required=False, no_log=True),

        old_ssh_version=dict(type='bool', default=False, required=False),
    )
    return options


def raise_timeout(name=''):
    def decorate(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError(f'{name} timed out, wait {timeout}s')

            timeout = getattr(self, 'timeout', 0)
            try:
                if timeout > 0:
                    signal.signal(signal.SIGALRM, handler)
                    signal.alarm(timeout)
                return func(self, *args, **kwargs)
            finally:
                if timeout > 0:
                    signal.alarm(0)

        return wrapper

    return decorate


def _strip_wrapping_quotes(value):
    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def normalize_gateway_args_for_legacy_parser(gateway_args):
   
    return re.sub(
        r'(-W\s+%h:%p\s+-q)\s+--\s+([^@\s]+@[^\'"\s]+)([\'"]?)',
        r'\2 \1\3',
        gateway_args,
    )


def _build_switch_state_re():
    return re.compile(
        r'__JMS_SWITCH__:[^\r\n]*',
        flags=re.IGNORECASE,
    )


def _shorten_text(value, limit=300):
    if value is None:
        return value
    text = str(value).replace('\r', '\\r').replace('\n', '\\n')
    if len(text) <= limit:
        return text
    return text[:limit] + f'...<{len(text)} chars>'


def _extract_switch_state(output):
    if not output:
        return None
    matches = re.findall(r'__JMS_SWITCH__:[^\r\n]*', output)
    return matches[-1] if matches else None


class OldSSHTransport(paramiko.transport.Transport):
    _preferred_pubkeys = (
        "ssh-ed25519",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "ssh-rsa",
        "rsa-sha2-256",
        "rsa-sha2-512",
        "ssh-dss",
    )


class SSHClient:
    def __init__(self, module):
        self.module = module
        self.gateway_server = None
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.debug_enabled = (
            str(os.environ.get('JMS_REMOTE_CLIENT_DEBUG', '')).lower()
            in {'1', 'true', 'yes', 'on'}
        )
        self.connect_params = self.get_connect_params()
        self._channel = None

        self.buffer_size = 1024
        self.prompt = self.module.params['prompt']
        self.timeout = self.module.params['recv_timeout']
        self._debug(
            'init',
            login_host=self.module.params.get('login_host'),
            login_port=self.module.params.get('login_port'),
            login_user=self.module.params.get('login_user'),
            become=self.module.params.get('become'),
            become_method=self.module.params.get('become_method'),
            become_user=self.module.params.get('become_user'),
            has_gateway=bool(self.module.params.get('gateway_args')),
            old_ssh_version=self.module.params.get('old_ssh_version'),
        )

    def _debug(self, event, **kwargs):
        if not self.debug_enabled:
            return
        details = ', '.join(
            f'{key}={_shorten_text(value)}'
            for key, value in kwargs.items()
        )
        message = f'[remote_client] {event}'
        if details:
            message += f' | {details}'
        print(message, file=sys.stderr, flush=True)

    def _sanitize_command(self, command):
        secrets = {
            self.module.params.get('login_password'),
            self.module.params.get('become_password'),
        }
        if command and command in secrets:
            return '<redacted>'
        return command

    @property
    def channel(self):
        if self._channel is None:
            self.connect()
        return self._channel

    def get_connect_params(self):
        p = self.module.params
        connect_timeout = p.get('recv_timeout', 60)
        params = {
            'allow_agent': False,
            'look_for_keys': False,
            'hostname': p['login_host'],
            'port': p['login_port'],
            'key_filename': p['login_private_key_path'] or None,
        }
        if connect_timeout:
            # Keep Paramiko connect/auth/banner waits bounded by the same
            # timeout budget as command receive so a bad host returns promptly.
            params.update(
                timeout=connect_timeout,
                auth_timeout=connect_timeout,
                banner_timeout=connect_timeout,
            )

        if p['become']:
            params['username'] = p['become_user']
            params['password'] = p['become_password']
            params['key_filename'] = p['become_private_key_path'] or None
        else:
            params['username'] = p['login_user']
            params['password'] = p['login_password']
            params['key_filename'] = p['login_private_key_path'] or None

        if p['old_ssh_version']:
            params['transport_factory'] = OldSSHTransport

        self._debug(
            'connect params prepared',
            hostname=params.get('hostname'),
            port=params.get('port'),
            username=params.get('username'),
            has_password=bool(params.get('password')),
            key_filename=params.get('key_filename'),
            transport_factory=getattr(params.get('transport_factory'), '__name__', None),
        )
        return params

    def switch_user(self):
        p = self.module.params
        if not p['become']:
            self._debug('switch user skipped', reason='become disabled')
            return

        method = p['become_method']
        username = p['login_user']
        self._debug(
            'switch user start',
            method=method,
            connect_as=self.connect_params.get('username'),
            target_user=username,
        )

        if method == 'sudo':
            switch_cmd = 'sudo su -'
            pword = p['become_password']
        elif method == 'su':
            switch_cmd = 'su -'
            pword = p['login_password']
        else:
            self._debug('switch user unsupported', method=method)
            self.module.fail_json(msg=f'Become method {method} not supported.')
            return

        # Username-based verification is unreliable for UID 0 alias accounts:
        # `su - useradmin` may legitimately land in a shell that reports
        # `root/root` for USER and LOGNAME. Compare shell state before and
        # after `su` instead; if password auth fails, the marker runs in the
        # original shell and the state stays unchanged.
        switch_state_cmd = 'printf "__JMS_SWITCH__:%s:%s:%s\\n" "$USER" "$LOGNAME" "$HOME"'
        switch_state_re = _build_switch_state_re()

        baseline_output, baseline_error = self.execute(
            [switch_state_cmd],
            [switch_state_re]
        )
        baseline_state = _extract_switch_state(baseline_output)
        self._debug(
            'switch user baseline',
            output=baseline_output,
            error=baseline_error,
            state=baseline_state,
        )
        if baseline_error:
            self.module.fail_json(msg=f'Failed to capture shell state before switching user. Output: {baseline_output}')

        # Expected to see a prompt, type the password, and verify the target
        # shell state is no longer the original login shell.
        output, error = self.execute(
            [f'{switch_cmd} {username}', pword, switch_state_cmd],
            [become_prompt_re, DEFAULT_RE, switch_state_re]
        )
        switched_state = _extract_switch_state(output)
        self._debug('switch user result', output=output, error=error)
        if error:
            self.module.fail_json(msg=f'Failed to become user {username}. Output: {output}')
        if baseline_state == switched_state:
            self.module.fail_json(
                msg=(
                    f'Failed to become user {username}. '
                    f'Shell state did not change. Output: {output}'
                )
            )

    def connect(self):
        try:
            self._debug(
                'connect start',
                hostname=self.connect_params.get('hostname'),
                port=self.connect_params.get('port'),
                username=self.connect_params.get('username'),
            )
            self.before_runner_start()
            self._debug(
                'connect after gateway prepare',
                hostname=self.connect_params.get('hostname'),
                port=self.connect_params.get('port'),
                username=self.connect_params.get('username'),
            )
            self.client.connect(**self.connect_params)
            self._debug('client.connect ok')
            self._channel = self.client.invoke_shell()
            self._debug('invoke_shell ok')
            # Always perform a gentle handshake that works for servers and
            # network devices: drain banner, brief settle, send newline, then
            # read in quiet mode to avoid blocking on missing prompt.
            try:
                while self._channel.recv_ready():
                    self._channel.recv(self.buffer_size)
            except Exception:
                pass
            time.sleep(0.5)
            try:
                self._channel.send(b'\n')
            except Exception:
                pass
            self._get_match_recv()
            self.switch_user()
            self._debug('connect complete')
        except Exception as error:
            self._debug(
                'connect failed',
                error=str(error),
                traceback=traceback.format_exc(),
            )
            self.module.fail_json(msg=str(error))

    @staticmethod
    def _fit_answers(commands, answers):
        if answers is None or not isinstance(answers, list):
            answers = [DEFAULT_RE] * len(commands)
        elif len(answers) < len(commands):
            answers += [DEFAULT_RE] * (len(commands) - len(answers))
        return answers

    @staticmethod
    def __match(expression, content):
        if isinstance(expression, str):
            expression = re.compile(expression, re.DOTALL | re.IGNORECASE)
        elif not isinstance(expression, re.Pattern):
            raise ValueError(f'{expression} should be a regular expression')

        return bool(expression.search(content))

    @raise_timeout('Recv message')
    def _get_match_recv(self, answer_reg=DEFAULT_RE):
        buffer_str = ''
        prev_str = ''
        last_change_ts = time.time()

        # Quiet-mode reading only when explicitly requested, or when both
        # answer regex and prompt are permissive defaults.
        use_regex_match = True
        if answer_reg == DEFAULT_RE and self.prompt == DEFAULT_RE:
            use_regex_match = False

        check_reg = self.prompt if answer_reg == DEFAULT_RE else answer_reg
        while True:
            if self.channel.recv_ready():
                chunk = self.channel.recv(self.buffer_size).decode('utf-8', 'replace')
                if chunk:
                    buffer_str += chunk
                    last_change_ts = time.time()

            if buffer_str and buffer_str != prev_str:
                if use_regex_match:
                    if self.__match(check_reg, buffer_str):
                        break
                else:
                    # Wait for a brief quiet period to approximate completion
                    if time.time() - last_change_ts > 0.3:
                        break
            elif not use_regex_match and buffer_str:
                # In quiet mode with some data already seen, also break after
                # a brief quiet window even if buffer hasn't changed this loop.
                if time.time() - last_change_ts > 0.3:
                    break
            elif not use_regex_match and not buffer_str:
                # No data at all in quiet mode; bail after short wait
                if time.time() - last_change_ts > 1.0:
                    break

            prev_str = buffer_str
            time.sleep(0.01)

        self._debug(
            'recv complete',
            use_regex_match=use_regex_match,
            check_reg=check_reg,
            output=buffer_str,
        )
        return buffer_str

    @raise_timeout('Wait send message')
    def _check_send(self):
        while not self.channel.send_ready():
            time.sleep(0.01)
        time.sleep(self.module.params['delay_time'])

    def execute(self, commands, answers=None):
        combined_output = ''
        error_msg = ''

        try:
            answers = self._fit_answers(commands, answers)
            self._debug('execute start', total_commands=len(commands))
            for index, (cmd, ans_regex) in enumerate(zip(commands, answers), start=1):
                self._check_send()
                self._debug(
                    'execute send',
                    index=index,
                    command=self._sanitize_command(cmd),
                    answer_reg=ans_regex,
                )
                self.channel.send(cmd + '\n')
                output = self._get_match_recv(ans_regex)
                combined_output += output + '\n'
                self._debug('execute recv', index=index, output=output)

        except Exception as e:
            error_msg = str(e)
            self._debug(
                'execute failed',
                error=error_msg,
                traceback=traceback.format_exc(),
            )

        return combined_output, error_msg

    def local_gateway_prepare(self):
        gateway_args = self.module.params['gateway_args'] or ''
        gateway_args = normalize_gateway_args_for_legacy_parser(gateway_args)
        pattern = (
            r"(?:sshpass -p ([^ ]+))?\s*ssh -o Port=(\d+)\s+-o StrictHostKeyChecking=no\s+"
            r"([^@\s]+)@([^\s]+)\s+-W %h:%p -q(?: -i ([^']+))?'"
        )
        match = re.search(pattern, gateway_args)
        if not match:
            if gateway_args:
                self._debug('gateway parse skipped', gateway_args=gateway_args)
            return

        password, port, username, remote_addr, key_path = match.groups()
        password = _strip_wrapping_quotes(password) or None
        key_path = _strip_wrapping_quotes(key_path) or None
        self._debug(
            'gateway parsed',
            gateway_host=remote_addr,
            gateway_port=port,
            gateway_user=username,
            has_password=bool(password),
            key_path=key_path,
            remote_bind_host=self.module.params['login_host'],
            remote_bind_port=self.module.params['login_port'],
        )

        server = SSHTunnelForwarder(
            (remote_addr, int(port)),
            ssh_username=username,
            ssh_password=password,
            ssh_pkey=key_path,
            remote_bind_address=(
                self.module.params['login_host'],
                self.module.params['login_port']
            )
        )

        try:
            server.start()
        except Exception:
            self._debug('gateway start failed', traceback=traceback.format_exc())
            raise
        self.connect_params['hostname'] = '127.0.0.1'
        self.connect_params['port'] = server.local_bind_port
        self.gateway_server = server
        self._debug(
            'gateway start ok',
            local_bind_host=self.connect_params['hostname'],
            local_bind_port=self.connect_params['port'],
        )

    def local_gateway_clean(self):
        if self.gateway_server:
            self._debug('gateway stop start')
            self.gateway_server.stop()
            self._debug('gateway stop ok')

    def before_runner_start(self):
        self.local_gateway_prepare()

    def after_runner_end(self):
        self.local_gateway_clean()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.after_runner_end()
            if self.channel:
                self.channel.close()
            if self.client:
                self.client.close()
        except Exception:  # noqa
            self._debug('cleanup failed', traceback=traceback.format_exc())
