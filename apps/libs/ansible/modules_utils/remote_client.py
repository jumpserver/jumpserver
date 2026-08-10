import codecs
import json
import os
import re
import shlex
import signal
import sys
import threading
import time
import traceback
from functools import wraps

import paramiko

from libs.ansible.modules_utils.ssh_tunnel import TimeoutSSHTunnelForwarder

DEFAULT_RE = '.*'
SUDO_PROMPT_MARKER = '__JMS_SUDO_PROMPT__:'
SUDO_PROMPT_SHELL_ARG = "'__JMS_SUDO_''PROMPT__:'"
SWITCH_STATE_MARKER = '__JMS_SWITCH_STATE__:'
NETWORK_BECOME_COMMANDS = {
    'enable': 'enable',
    'super': 'super 15',
    'super_level': 'super level 15',
}
TRUE_ENV_VALUES = frozenset({'1', 'true', 'yes', 'on'})
DEBUG_EVENT_LIMIT = 200
DEBUG_FIELD_LIMITS = {
    'output': 600,
    'traceback': 1500,
}
sudo_prompt_re = re.compile(re.escape(SUDO_PROMPT_MARKER))
su_prompt_re = re.compile(
    r"(?:^|[\r\n])(?:"
    r"(?:[^\r\n]{1,128}['’]s\s+)?Password"
    r"|Password\s+for\s+[^\r\n:：]{1,128}"
    r")\s*[:：]\s*$",
    flags=re.IGNORECASE,
)
become_auth_failure_re = re.compile(
    r'(?:^|[\r\n])\s*(?:'
    r'su:\s*(?:authentication fail(?:ure|ed)|incorrect password|sorry\b)'
    r'|sudo:\s*(?:\d+\s+)?incorrect password attempts?'
    r'|sorry,\s*try again\.?'
    r')\s*(?=[\r\n]|$)',
    flags=re.IGNORECASE | re.MULTILINE,
)
network_auth_failure_re = re.compile(
    r'(?:^|[\r\n])\s*(?:'
    r'%?\s*(?:access denied|authentication failed|bad passwords?|'
    r'incorrect password|password (?:is )?incorrect|wrong password)'
    r'|error\s*:\s*[^\r\n]*password'
    r')\s*[.!]?\s*(?=[\r\n]|$)',
    flags=re.IGNORECASE | re.MULTILINE,
)
network_command_failure_re = re.compile(
    r'(?:^|[\r\n])\s*(?:'
    r'%\s*(?:invalid|unknown|unrecognized|incomplete|ambiguous)\b'
    r'|error\s*:\s*[^\r\n]+'
    r')',
    flags=re.IGNORECASE | re.MULTILINE,
)


class BecomeAuthenticationError(paramiko.AuthenticationException):
    """The target account rejected a privilege-switch credential."""


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
        auth_only=dict(type='bool', default=False, required=False),
        fail_on_unknown=dict(type='bool', default=True, required=False),
        change_succeeded=dict(type='bool', default=True, required=False),
    )
    return options


def raise_timeout(name=''):
    def decorate(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError(f'{name} timed out, wait {timeout}s')

            timeout = float(getattr(self, 'timeout', 0) or 0)
            can_use_alarm = (
                timeout > 0
                and hasattr(signal, 'SIGALRM')
                and hasattr(signal, 'ITIMER_REAL')
                and threading.current_thread() is threading.main_thread()
            )
            if not can_use_alarm:
                return func(self, *args, **kwargs)

            previous_handler = signal.getsignal(signal.SIGALRM)
            previous_delay, previous_interval = signal.getitimer(
                signal.ITIMER_REAL
            )
            effective_timeout = timeout
            if previous_delay > 0:
                effective_timeout = min(effective_timeout, previous_delay)
            started_at = time.monotonic()
            try:
                signal.signal(signal.SIGALRM, handler)
                signal.setitimer(signal.ITIMER_REAL, effective_timeout)
                return func(self, *args, **kwargs)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)
                if previous_delay > 0:
                    elapsed = time.monotonic() - started_at
                    remaining = previous_delay - elapsed
                    if remaining > 0:
                        signal.setitimer(
                            signal.ITIMER_REAL,
                            remaining,
                            previous_interval,
                        )

        return wrapper

    return decorate


def _unescape_ssh_config_percent(value):
    if value is None:
        return None
    return value.replace('%%', '%')


def _extract_proxy_command(gateway_args):
    try:
        args = shlex.split(gateway_args)
    except ValueError as error:
        raise ValueError('Invalid SSH gateway arguments') from error

    for index, arg in enumerate(args):
        option = arg
        if arg == '-o':
            if index + 1 >= len(args):
                raise ValueError('Invalid SSH gateway arguments')
            option = args[index + 1]
        elif arg.startswith('-o') and len(arg) > 2:
            option = arg[2:]

        key, separator, value = option.partition('=')
        if separator and key.lower() == 'proxycommand':
            return value
    return None


def _parse_gateway_args(gateway_args):
    proxy_command = _extract_proxy_command(gateway_args)
    if proxy_command is None:
        return None

    try:
        args = shlex.split(proxy_command)
    except ValueError as error:
        raise ValueError('Invalid SSH gateway ProxyCommand') from error
    if not args:
        raise ValueError('Empty SSH gateway ProxyCommand')

    password = None
    if os.path.basename(args[0]) == 'sshpass':
        if len(args) < 4 or args[1] != '-p':
            raise ValueError('Unsupported sshpass gateway arguments')
        password = args[2]
        args = args[3:]

    if not args or os.path.basename(args[0]) != 'ssh':
        raise ValueError('Unsupported SSH gateway ProxyCommand')

    port = 22
    key_path = None
    option_user = None
    target = None
    options_with_value = {
        '-B', '-b', '-c', '-D', '-E', '-e', '-F', '-I', '-i',
        '-J', '-L', '-l', '-m', '-O', '-o', '-P', '-p', '-Q', '-R', '-S',
        '-W', '-w',
    }
    index = 1
    while index < len(args):
        arg = args[index]
        if arg == '--':
            if target is None and index + 1 < len(args):
                target = args[index + 1]
            break

        if arg in options_with_value:
            if index + 1 >= len(args):
                raise ValueError('Invalid SSH gateway ProxyCommand')
            value = args[index + 1]
            if arg == '-i':
                key_path = value
            elif arg == '-l':
                option_user = value
            elif arg == '-p':
                port = value
            elif arg == '-o':
                option_name, separator, option_value = value.partition('=')
                if separator and option_name.lower() == 'port':
                    port = option_value
            index += 2
            continue

        if arg.startswith('-o') and len(arg) > 2:
            option_name, separator, option_value = arg[2:].partition('=')
            if separator and option_name.lower() == 'port':
                port = option_value
        elif arg.startswith('-i') and len(arg) > 2:
            key_path = arg[2:]
        elif arg.startswith('-l') and len(arg) > 2:
            option_user = arg[2:]
        elif arg.startswith('-p') and len(arg) > 2:
            port = arg[2:]
        elif not arg.startswith('-') and target is None:
            target = arg
        index += 1

    if not target:
        raise ValueError('SSH gateway target is missing')

    if '@' in target:
        username, remote_addr = target.rsplit('@', 1)
    else:
        username, remote_addr = option_user, target
    if not username or not remote_addr:
        raise ValueError('SSH gateway username or address is missing')
    if remote_addr.startswith('[') and remote_addr.endswith(']'):
        remote_addr = remote_addr[1:-1]

    try:
        port = int(_unescape_ssh_config_percent(str(port)))
    except (TypeError, ValueError) as error:
        raise ValueError('Invalid SSH gateway port') from error
    if not 1 <= port <= 65535:
        raise ValueError('Invalid SSH gateway port')

    return {
        'password': _unescape_ssh_config_percent(password),
        'port': port,
        'username': _unescape_ssh_config_percent(username),
        'remote_addr': _unescape_ssh_config_percent(remote_addr),
        'key_path': _unescape_ssh_config_percent(key_path),
    }


def _build_switch_state_re():
    return re.compile(
        re.escape(SWITCH_STATE_MARKER) + r'[^\r\n]*',
        flags=re.IGNORECASE,
    )


def _shorten_text(value, limit=300):
    if value is None:
        return value
    text = str(value).replace('\r', '\\r').replace('\n', '\\n')
    if len(text) <= limit:
        return text
    return text[:limit] + f'...<{len(text)} chars>'


def _env_flag_enabled(name):
    value = os.environ.get(name, '')
    return str(value).strip().lower() in TRUE_ENV_VALUES


def _extract_switch_state(output):
    if not output:
        return None
    matches = re.findall(
        re.escape(SWITCH_STATE_MARKER) + r'[^\r\n]*',
        output,
    )
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
        self.debug_enabled = _env_flag_enabled('JMS_REMOTE_CLIENT_DEBUG')
        self._debug_started_at = time.monotonic()
        self._debug_sequence = 0
        self._channel = None
        self._extra_secrets = set()

        self.buffer_size = 1024
        self.prompt = self.module.params['prompt']
        try:
            self._prompt_re = re.compile(
                self.prompt,
                re.DOTALL | re.IGNORECASE,
            )
        except (re.error, TypeError) as error:
            raise ValueError('Invalid SSH prompt regular expression') from error
        self.timeout = int(self.module.params.get('recv_timeout') or 0)
        self.delay_time = int(self.module.params.get('delay_time') or 0)
        if self.timeout <= 0:
            raise ValueError('recv_timeout must be greater than zero')
        if self.delay_time < 0:
            raise ValueError('delay_time cannot be negative')
        if self.delay_time >= self.timeout:
            raise ValueError('delay_time must be less than recv_timeout')
        self._last_command_sent_at = None
        self._decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self._debug(
            'client.init',
            login_host=self.module.params.get('login_host'),
            login_port=self.module.params.get('login_port'),
            login_user=self.module.params.get('login_user'),
            become=self.module.params.get('become'),
            become_method=self.module.params.get('become_method'),
            become_user=self.module.params.get('become_user'),
            has_gateway=bool(self.module.params.get('gateway_args')),
            old_ssh_version=self.module.params.get('old_ssh_version'),
        )
        self.connect_params = self.get_connect_params()

    def _known_secrets(self):
        secrets = {
            self.module.params.get('login_password'),
            self.module.params.get('become_password'),
            self.module.params.get('password'),
            self.module.params.get('login_private_key_path'),
            self.module.params.get('become_private_key_path'),
        }
        secrets.update(self._extra_secrets)
        return sorted(
            (
                str(secret)
                for secret in secrets
                if secret is not None and str(secret)
            ),
            key=len,
            reverse=True,
        )

    def _redact_text(self, value):
        if value is None:
            return value
        text = str(value)
        for secret in self._known_secrets():
            if len(secret) < 3:
                text = re.sub(
                    rf'(?<!\w){re.escape(secret)}(?!\w)',
                    '<redacted>',
                    text,
                )
            else:
                text = text.replace(secret, '<redacted>')
        return text

    def _debug(self, event, **kwargs):
        if not self.debug_enabled:
            return
        # Debugging must never change the SSH result. Keep every field on one
        # JSON line so concurrent hosts remain searchable and machine-readable.
        try:
            if self._debug_sequence >= DEBUG_EVENT_LIMIT:
                return
            self._debug_sequence += 1
            if self._debug_sequence == DEBUG_EVENT_LIMIT:
                event = 'debug.truncated'
                kwargs = {'event_limit': DEBUG_EVENT_LIMIT}
            params = self.module.params
            target = '{}:{}'.format(
                params.get('login_host') or '',
                params.get('login_port') or '',
            )
            payload = {
                'event': str(event or 'unknown'),
                'sequence': self._debug_sequence,
                'elapsed_ms': int(
                    (time.monotonic() - self._debug_started_at) * 1000
                ),
                'pid': os.getpid(),
                'target': target,
            }
            for key, value in kwargs.items():
                if value is None or isinstance(value, (bool, int, float)):
                    payload[str(key)] = value
                    continue
                limit = DEBUG_FIELD_LIMITS.get(key, 300)
                payload[str(key)] = _shorten_text(
                    self._redact_text(value),
                    limit=limit,
                )
            message = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(',', ':'),
            )
            message = f'[remote_client] {message}'
            warn = getattr(self.module, 'warn', None)
            if callable(warn):
                # Successful module stderr is discarded by Ansible. Warnings
                # are retained in the module result and displayed in job logs.
                warn(message)
            else:
                print(message, file=sys.stderr, flush=True)
        except Exception:
            # A broken warning/stderr sink or an unexpected debug value must
            # not turn a successful authentication/change into a failed task.
            return

    def _sanitize_command(self, command):
        if command and any(
            secret in str(command) for secret in self._known_secrets()
        ):
            return '<redacted>'
        return command

    @property
    def channel(self):
        if self._channel is None:
            self.connect(raise_on_error=True)
        if self._channel is None:
            raise RuntimeError('SSH shell channel is not available')
        return self._channel

    def get_connect_params(self):
        p = self.module.params
        connect_timeout = self.timeout
        hostname = p['login_host']
        port = int(p['login_port'])
        if not hostname:
            raise ValueError('SSH login host is required')
        if not 1 <= port <= 65535:
            raise ValueError('SSH login port must be between 1 and 65535')
        params = {
            'allow_agent': False,
            'look_for_keys': False,
            'hostname': hostname,
            'port': port,
            'key_filename': p['login_private_key_path'] or None,
        }
        if connect_timeout:
            # Keep Paramiko connect/auth/banner waits bounded by the same
            # timeout budget as command receive so a bad host returns promptly.
            params.update(
                timeout=connect_timeout,
                auth_timeout=connect_timeout,
                banner_timeout=connect_timeout,
                channel_timeout=connect_timeout,
            )

        # Historical remote_client contract:
        #   become_* = the source credential used for the SSH connection
        #   login_*  = the final target account reached after su/sudo
        # Keep this explicit because it is the inverse of Ansible's usual
        # variable naming and changing it would break host and network-device
        # callers.
        if p['become']:
            params['username'] = p['become_user']
            params['password'] = p['become_password']
            params['key_filename'] = p['become_private_key_path'] or None
        else:
            params['username'] = p['login_user']
            params['password'] = p['login_password']
            params['key_filename'] = p['login_private_key_path'] or None
        if not params['username']:
            raise ValueError('SSH login username is required')

        if p['old_ssh_version']:
            params['transport_factory'] = OldSSHTransport

        self._debug(
            'connect.params',
            hostname=params.get('hostname'),
            port=params.get('port'),
            username=params.get('username'),
            has_password=bool(params.get('password')),
            has_private_key=bool(params.get('key_filename')),
            transport_factory=getattr(params.get('transport_factory'), '__name__', None),
        )
        return params

    def _switch_network_privilege(self, method):
        switch_cmd = NETWORK_BECOME_COMMANDS[method]
        password = self.module.params.get('login_password')
        channel = self.channel

        self._debug(
            'privilege.network.start',
            method=method,
            command=switch_cmd,
        )
        self._check_send(channel)
        self._send_command(channel, switch_cmd)
        switch_output = self._get_match_recv(
            su_prompt_re,
            allow_quiet=True,
            quiet_period=max(1.0, float(self.delay_time)),
        )
        prompt_seen = self.__match(su_prompt_re, switch_output)
        result_output = switch_output

        if prompt_seen:
            if password is None or str(password) == '':
                raise RuntimeError(
                    f'Password is required for {method} privilege switching'
                )
            password = str(password)
            if '\r' in password or '\n' in password:
                raise ValueError(
                    'The privilege password cannot contain a line break'
                )
            self._check_send(channel)
            self._send_command(channel, password)
            # The privileged prompt often differs from the login prompt
            # (`>` becomes `#`), so allow quiet completion here.
            password_output = self._get_match_recv(allow_quiet=True)
            result_output += '\n' + password_output
            if (
                self.__match(su_prompt_re, password_output)
                or network_auth_failure_re.search(password_output)
            ):
                raise BecomeAuthenticationError(
                    f'Password was rejected during {method} privilege switching'
                )
        elif network_auth_failure_re.search(switch_output):
            raise BecomeAuthenticationError(
                f'Privilege switching with {method} was rejected'
            )

        if network_command_failure_re.search(result_output):
            raise RuntimeError(
                f'Device rejected the {method} privilege-switch command'
            )
        if not result_output.strip():
            raise RuntimeError(
                f'No response received during {method} privilege switching'
            )
        self._debug(
            'privilege.network.complete',
            method=method,
            output=result_output,
        )

    def switch_user(self):
        p = self.module.params
        if not p['become']:
            self._debug(
                'privilege.user.skipped',
                reason='become disabled',
            )
            return

        method = p['become_method']
        username = p['login_user']
        if method in NETWORK_BECOME_COMMANDS:
            self._switch_network_privilege(method)
            return
        if (
            not isinstance(username, str)
            or not username
            or any(char in username for char in '\x00\r\n')
        ):
            raise ValueError('Invalid target username for su/sudo')
        quoted_username = shlex.quote(username)
        self._debug(
            'privilege.user.start',
            method=method,
            connect_as=self.connect_params.get('username'),
            target_user=username,
        )

        if method == 'sudo':
            switch_cmd = (
                f'env LC_ALL=C LANG=C '
                f'sudo -S -p {SUDO_PROMPT_SHELL_ARG} '
                f'su - {quoted_username}'
            )
            prompt_re = sudo_prompt_re
            pword = p['become_password']
        elif method == 'su':
            # Use the standard POSIX locale so prompt detection does not
            # depend on a hard-coded list of translated password strings.
            switch_cmd = (
                f'env LC_ALL=C LANG=C su - {quoted_username}'
            )
            prompt_re = su_prompt_re
            pword = p['login_password']
        else:
            self._debug('privilege.user.unsupported', method=method)
            raise ValueError(f'Become method {method} not supported.')

        # Username-based verification is unreliable for UID 0 alias accounts:
        # `su - useradmin` may legitimately land in a shell that reports
        # `root/root` for USER and LOGNAME. Compare shell state before and
        # after `su` instead; if password auth fails, the marker runs in the
        # original shell and the state stays unchanged.
        # Split the marker inside the command so terminal command echo cannot
        # satisfy the result regex before printf has actually run.
        switch_state_cmd = (
            "printf '__JMS_SWITCH_''STATE__:%s:%s:%s\\n' "
            '"$USER" "$LOGNAME" "$HOME"'
        )
        switch_state_re = _build_switch_state_re()

        baseline_output, baseline_error = self.execute(
            [switch_state_cmd],
            [switch_state_re]
        )
        baseline_state = _extract_switch_state(baseline_output)
        self._debug(
            'privilege.user.baseline',
            output=baseline_output,
            error=baseline_error,
            state=baseline_state,
        )
        if baseline_error:
            raise RuntimeError(
                'Failed to capture shell state before switching user. '
                f'Output: {self._redact_text(baseline_output)}. '
                f'Error: {self._redact_text(baseline_error)}'
            )
        if baseline_state is None:
            raise RuntimeError(
                'Failed to capture shell state before switching user. '
                'The login shell did not return a verification marker.'
            )

        # A root `su` or NOPASSWD sudo may open the target shell without
        # displaying a password prompt. Read until either the deterministic
        # prompt appears or the channel becomes quiet, then only send the
        # secret when a prompt was actually observed.
        output_parts = []
        error = ''
        authentication_error = None
        password_sent = False
        try:
            channel = self.channel
            self._check_send(channel)
            self._send_command(channel, switch_cmd)
            switch_output = self._get_match_recv(
                prompt_re,
                allow_quiet=True,
                quiet_period=max(1.0, float(self.delay_time)),
            )
            output_parts.append(switch_output)

            if self.__match(prompt_re, switch_output):
                if pword is None or str(pword) == '':
                    raise RuntimeError(
                        f'Password is required to become user {username}'
                    )
                if '\r' in str(pword) or '\n' in str(pword):
                    raise ValueError(
                        'The become password cannot contain a line break'
                    )
                self._check_send(channel)
                self._send_command(channel, str(pword))
                password_sent = True
                password_output = self._get_match_recv(
                    prompt_re,
                    allow_quiet=True,
                )
                output_parts.append(password_output)
                if (
                    self.__match(prompt_re, password_output)
                    or become_auth_failure_re.search(password_output)
                ):
                    raise BecomeAuthenticationError(
                        f'Password was rejected while becoming user {username}'
                    )

            self._check_send(channel)
            self._send_command(channel, switch_state_cmd)
            output_parts.append(self._get_match_recv(switch_state_re))
        except BecomeAuthenticationError as exception:
            authentication_error = exception
            error = str(exception)
        except Exception as exception:
            error = str(exception)

        output = '\n'.join(output_parts)
        switched_state = _extract_switch_state(output)
        if (
            authentication_error is None
            and password_sent
            and become_auth_failure_re.search(output)
        ):
            authentication_error = BecomeAuthenticationError(
                f'Password was rejected while becoming user {username}'
            )
        self._debug(
            'privilege.user.result',
            output=output,
            error=error,
        )
        if authentication_error is not None:
            raise authentication_error
        if error:
            safe_output = self._redact_text(output)
            raise RuntimeError(
                f'Failed to become user {username}. Output: {safe_output}. '
                f'Error: {self._redact_text(error)}'
            )
        if switched_state is None:
            raise RuntimeError(
                f'Failed to become user {username}. '
                'The switched shell did not return a verification marker.'
            )
        if baseline_state == switched_state:
            raise RuntimeError(
                f'Failed to become user {username}. '
                f'Shell state did not change. '
                f'Output: {self._redact_text(output)}'
            )

    def _transport_is_ready(self):
        get_transport = getattr(self.client, 'get_transport', None)
        if not get_transport:
            return False
        transport = get_transport()
        if transport is None or not transport.is_active():
            return False
        is_authenticated = getattr(transport, 'is_authenticated', None)
        if is_authenticated is None:
            return True
        if callable(is_authenticated):
            return bool(is_authenticated())
        return bool(is_authenticated)

    @raise_timeout('SSH connect')
    def _connect_client(self):
        self.client.connect(**self.connect_params)

    def connect(self, auth_only=False, raise_on_error=False):
        try:
            self._debug(
                'connect.start',
                hostname=self.connect_params.get('hostname'),
                port=self.connect_params.get('port'),
                username=self.connect_params.get('username'),
            )
            if not self._transport_is_ready():
                self.before_runner_start()
                self._debug(
                    'connect.prepared',
                    hostname=self.connect_params.get('hostname'),
                    port=self.connect_params.get('port'),
                    username=self.connect_params.get('username'),
                    has_gateway=bool(self.gateway_server),
                )
                self._connect_client()
                self._debug('connect.authenticated')
            else:
                self._debug('connect.transport_reused')

            # A successful Paramiko connect is sufficient proof that the
            # supplied password/key was accepted. Opening an interactive shell
            # here creates false negatives on restricted shells and network
            # devices with non-POSIX prompts. Accounts reached through any
            # become flow still need the shell phase because SSH authenticated
            # their source account.
            if auth_only and not self.module.params.get('become'):
                self._debug('connect.complete', mode='auth_only')
                return

            if (
                self._channel is not None
                and not self._channel_is_closed(self._channel)
            ):
                self._debug('connect.complete', mode='shell_reused')
                return

            self._channel = self.client.invoke_shell()
            self._decoder = codecs.getincrementaldecoder('utf-8')('replace')
            if self.timeout > 0:
                self._channel.settimeout(self.timeout)
            self._debug('connect.shell_opened')
            # Always perform a gentle handshake that works for servers and
            # network devices: drain banner, brief settle, send newline, then
            # read in quiet mode to avoid blocking on missing prompt.
            while self._channel.recv_ready():
                if not self._channel.recv(self.buffer_size):
                    break
            time.sleep(0.5)
            self._channel.sendall(b'\n')
            self._last_command_sent_at = time.monotonic()
            self._get_match_recv()
            if self._channel_is_closed(self._channel):
                raise EOFError('SSH shell channel closed during handshake')
            self.switch_user()
            self._debug('connect.complete', mode='interactive_shell')
        except Exception as error:
            self._debug(
                'connect.failed',
                error_type=type(error).__name__,
                error=str(error),
                traceback=traceback.format_exc(),
            )
            if raise_on_error:
                raise
            self.module.fail_json(msg=self._redact_text(error))

    @staticmethod
    def _fit_answers(commands, answers):
        if answers is None:
            result = []
        elif isinstance(answers, (str, re.Pattern)):
            result = [answers]
        elif isinstance(answers, (list, tuple)):
            result = list(answers)
        else:
            raise ValueError('Answers must be a regular expression or a list')

        if len(result) < len(commands):
            result.extend([DEFAULT_RE] * (len(commands) - len(result)))
        return result

    @staticmethod
    def __match(expression, content):
        if isinstance(expression, str):
            expression = re.compile(expression, re.DOTALL | re.IGNORECASE)
        elif not isinstance(expression, re.Pattern):
            raise ValueError(f'{expression} should be a regular expression')

        return bool(expression.search(content))

    @staticmethod
    def _channel_is_closed(channel):
        return bool(
            getattr(channel, 'closed', False)
            or getattr(channel, 'eof_received', False)
        )

    @raise_timeout('Recv message')
    def _get_match_recv(
        self,
        answer_reg=DEFAULT_RE,
        allow_quiet=False,
        quiet_period=None,
    ):
        buffer_str = ''
        started_at = time.monotonic()
        last_change_ts = started_at
        channel = self.channel
        if quiet_period is None:
            # Keep the channel quiet long enough to catch delayed device
            # output, while counting that wait toward the configured pacing.
            quiet_period = max(
                0.3,
                min(float(self.delay_time), 1.0),
            )

        # Quiet-mode reading only when explicitly requested, or when both
        # answer regex and prompt are permissive defaults.
        use_regex_match = True
        if answer_reg == DEFAULT_RE and self.prompt == DEFAULT_RE:
            use_regex_match = False

        check_reg = (
            self._prompt_re
            if answer_reg == DEFAULT_RE and self.prompt != DEFAULT_RE
            else answer_reg
        )
        if use_regex_match and isinstance(check_reg, str):
            check_reg = re.compile(
                check_reg, re.DOTALL | re.IGNORECASE
            )
        while True:
            saw_eof = False
            reads = 0
            while channel.recv_ready() and reads < 256:
                data = channel.recv(self.buffer_size)
                reads += 1
                if not data:
                    saw_eof = True
                    break
                if isinstance(data, str):
                    chunk = data
                else:
                    chunk = self._decoder.decode(data)
                if chunk:
                    buffer_str += chunk
                    last_change_ts = time.monotonic()

            expression_matched = (
                use_regex_match
                and buffer_str
                and self.__match(check_reg, buffer_str)
            )
            if expression_matched:
                break

            now = time.monotonic()
            if self._channel_is_closed(channel) or saw_eof:
                tail = self._decoder.decode(b'', final=True)
                if tail:
                    buffer_str += tail
                if (
                    use_regex_match
                    and buffer_str
                    and self.__match(check_reg, buffer_str)
                ):
                    break
                if not use_regex_match and buffer_str:
                    break
                raise EOFError('SSH shell channel closed')

            quiet_mode = not use_regex_match or allow_quiet
            if quiet_mode:
                if buffer_str and now - last_change_ts > quiet_period:
                    break
                if (
                    not buffer_str
                    and now - started_at > max(1.0, quiet_period)
                ):
                    break

            if self.timeout > 0 and now - started_at >= self.timeout:
                raise TimeoutError(
                    f'Recv message timed out, wait {self.timeout}s'
                )
            time.sleep(0.01)

        self._debug(
            'receive.complete',
            duration_ms=int((time.monotonic() - started_at) * 1000),
            output_chars=len(buffer_str),
            use_regex_match=use_regex_match,
            check_reg=check_reg,
            output=buffer_str,
        )
        return buffer_str

    @raise_timeout('Wait send message')
    def _check_send(self, channel):
        started_at = time.monotonic()
        while not channel.send_ready():
            if self._channel_is_closed(channel):
                raise EOFError('SSH shell channel closed')
            if (
                self.timeout > 0
                and time.monotonic() - started_at >= self.timeout
            ):
                raise TimeoutError(
                    f'Wait send message timed out, wait {self.timeout}s'
                )
            time.sleep(0.01)

        if self._channel_is_closed(channel):
            raise EOFError('SSH shell channel closed')
        if self._last_command_sent_at is None:
            return
        elapsed = time.monotonic() - self._last_command_sent_at
        remaining = self.delay_time - elapsed
        while remaining > 0:
            if self._channel_is_closed(channel):
                raise EOFError('SSH shell channel closed')
            if (
                self.timeout > 0
                and time.monotonic() - started_at >= self.timeout
            ):
                raise TimeoutError(
                    f'Wait send message timed out, wait {self.timeout}s'
                )
            time.sleep(min(remaining, 0.05))
            elapsed = time.monotonic() - self._last_command_sent_at
            remaining = self.delay_time - elapsed

    @raise_timeout('Send message')
    def _send_command(self, channel, command):
        if not isinstance(command, str):
            raise ValueError('SSH command must be a string')
        if self._channel_is_closed(channel):
            raise EOFError('SSH shell channel closed')
        channel.sendall((command + '\n').encode('utf-8'))
        self._last_command_sent_at = time.monotonic()

    def execute(self, commands, answers=None):
        output_parts = []
        error_msg = ''
        started_at = time.monotonic()

        try:
            if isinstance(commands, str):
                commands = [commands]
            elif isinstance(commands, (list, tuple)):
                commands = list(commands)
            else:
                raise ValueError('Commands must be a string or a list')
            if not commands:
                return '', ''
            if any(not isinstance(command, str) for command in commands):
                raise ValueError('Every SSH command must be a string')
            answers = self._fit_answers(commands, answers)
            for index, answer in enumerate(answers):
                if answer == DEFAULT_RE:
                    continue
                if isinstance(answer, str):
                    try:
                        answers[index] = re.compile(
                            answer,
                            re.DOTALL | re.IGNORECASE,
                        )
                    except re.error as error:
                        raise ValueError(
                            'Invalid answer regular expression'
                        ) from error
                elif not isinstance(answer, re.Pattern):
                    raise ValueError(
                        f'{answer} should be a regular expression'
                    )
            channel = self.channel
            self._debug(
                'command.batch_start',
                total_commands=len(commands),
            )
            for index, (cmd, ans_regex) in enumerate(zip(commands, answers), start=1):
                self._check_send(channel)
                self._debug(
                    'command.send',
                    index=index,
                    command=self._sanitize_command(cmd),
                    answer_reg=ans_regex,
                )
                self._send_command(channel, cmd)
                output = self._get_match_recv(ans_regex)
                output_parts.append(output)
                self._debug(
                    'command.receive',
                    index=index,
                    output=output,
                )
            self._debug(
                'command.batch_complete',
                total_commands=len(commands),
                duration_ms=int(
                    (time.monotonic() - started_at) * 1000
                ),
                output_chars=sum(len(output) for output in output_parts),
            )

        except Exception as e:
            error_msg = self._redact_text(e)
            self._debug(
                'command.batch_failed',
                error_type=type(e).__name__,
                error=error_msg,
                duration_ms=int(
                    (time.monotonic() - started_at) * 1000
                ),
                traceback=traceback.format_exc(),
            )

        combined_output = ''.join(output + '\n' for output in output_parts)
        return combined_output, error_msg

    def local_gateway_prepare(self):
        if self.gateway_server is not None:
            self._debug(
                'gateway.prepare_skipped',
                reason='already started',
            )
            return

        gateway_args = self.module.params['gateway_args'] or ''
        gateway = _parse_gateway_args(gateway_args)
        if gateway is None:
            if gateway_args:
                raise ValueError(
                    'Unsupported SSH gateway arguments: '
                    'ProxyCommand is required'
                )
            return

        password = gateway['password'] or None
        port = gateway['port']
        username = gateway['username']
        remote_addr = gateway['remote_addr']
        key_path = gateway['key_path'] or None
        self._extra_secrets.update(
            value for value in (password, key_path) if value
        )
        self._debug(
            'gateway.parsed',
            gateway_host=remote_addr,
            gateway_port=port,
            gateway_user=username,
            has_password=bool(password),
            has_private_key=bool(key_path),
            remote_bind_host=self.module.params['login_host'],
            remote_bind_port=self.module.params['login_port'],
        )

        gateway_connect_timeout = os.getenv(
            'JMS_SSH_GATEWAY_CONNECT_TIMEOUT'
        )
        if not gateway_connect_timeout:
            gateway_connect_timeout = self.timeout
        server = TimeoutSSHTunnelForwarder(
            (remote_addr, port),
            ssh_username=username,
            ssh_password=password,
            ssh_pkey=key_path,
            connect_timeout=gateway_connect_timeout,
            remote_bind_address=(
                self.module.params['login_host'],
                self.module.params['login_port']
            ),
            local_bind_address=('127.0.0.1', 0),
        )

        try:
            server.start()
        except Exception as error:
            self._debug(
                'gateway.start_failed',
                error_type=type(error).__name__,
                error=str(error),
                traceback=traceback.format_exc(),
            )
            raise
        self.gateway_server = server
        self.connect_params['hostname'] = '127.0.0.1'
        self.connect_params['port'] = server.local_bind_port
        self._debug(
            'gateway.started',
            local_bind_host=self.connect_params['hostname'],
            local_bind_port=self.connect_params['port'],
        )

    def local_gateway_clean(self):
        server = self.gateway_server
        self.gateway_server = None
        if server:
            self._debug('gateway.stopping')
            try:
                server.stop(force=True)
            finally:
                self._debug('gateway.stopped')

    def before_runner_start(self):
        self.local_gateway_prepare()

    def after_runner_end(self):
        self.local_gateway_clean()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._channel is not None:
            try:
                self._channel.close()
            except Exception as error:  # noqa
                self._debug(
                    'cleanup.channel_failed',
                    error_type=type(error).__name__,
                    error=str(error),
                    traceback=traceback.format_exc(),
                )
            finally:
                self._channel = None

        try:
            if self.client:
                self.client.close()
        except Exception as error:  # noqa
            self._debug(
                'cleanup.client_failed',
                error_type=type(error).__name__,
                error=str(error),
                traceback=traceback.format_exc(),
            )

        try:
            # Close the target SSH channel and transport before its underlying
            # gateway tunnel.
            self.after_runner_end()
        except Exception as error:  # noqa
            self._debug(
                'cleanup.gateway_failed',
                error_type=type(error).__name__,
                error=str(error),
                traceback=traceback.format_exc(),
            )
