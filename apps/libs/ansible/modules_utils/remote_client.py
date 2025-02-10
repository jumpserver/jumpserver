import re
import signal
import time
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
            except Exception as error:
                signal.alarm(0)
                raise error

        return wrapper

    return decorate


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
        self.connect_params = self.get_connect_params()
        self._channel = None

        self.buffer_size = 1024
        self.prompt = self.module.params['prompt']
        self.timeout = self.module.params['recv_timeout']

    @property
    def channel(self):
        if self._channel is None:
            self.connect()
        return self._channel

    def get_connect_params(self):
        p = self.module.params
        params = {
            'allow_agent': False,
            'look_for_keys': False,
            'hostname': p['login_host'],
            'port': p['login_port'],
            'key_filename': p['login_private_key_path'] or None
        }

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

        return params

    def switch_user(self):
        p = self.module.params
        if not p['become']:
            return

        method = p['become_method']
        username = p['login_user']

        if method == 'sudo':
            switch_cmd = 'sudo su -'
            pword = p['become_password']
        elif method == 'su':
            switch_cmd = 'su -'
            pword = p['login_password']
        else:
            self.module.fail_json(msg=f'Become method {method} not supported.')
            return

        # Expected to see a prompt, type the password, and check the username
        output, error = self.execute(
            [f'{switch_cmd} {username}', pword, 'whoami'],
            [become_prompt_re, DEFAULT_RE, username]
        )
        if error:
            self.module.fail_json(msg=f'Failed to become user {username}. Output: {output}')

    def connect(self):
        self.before_runner_start()
        try:
            self.client.connect(**self.connect_params)
            self._channel = self.client.invoke_shell()
            self._get_match_recv()
            self.switch_user()
        except Exception as error:
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

        check_reg = self.prompt if answer_reg == DEFAULT_RE else answer_reg
        while True:
            if self.channel.recv_ready():
                chunk = self.channel.recv(self.buffer_size).decode('utf-8', 'replace')
                buffer_str += chunk

            if buffer_str and buffer_str != prev_str:
                if self.__match(check_reg, buffer_str):
                    break
            prev_str = buffer_str
            time.sleep(0.01)

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
            for cmd, ans_regex in zip(commands, answers):
                self._check_send()
                self.channel.send(cmd + '\n')
                combined_output += self._get_match_recv(ans_regex) + '\n'

        except Exception as e:
            error_msg = str(e)

        return combined_output, error_msg

    def local_gateway_prepare(self):
        gateway_args = self.module.params['gateway_args'] or ''
        pattern = (
            r"(?:sshpass -p ([^ ]+))?\s*ssh -o Port=(\d+)\s+-o StrictHostKeyChecking=no\s+"
            r"([\w@]+)@([\d.]+)\s+-W %h:%p -q(?: -i (.+))?'"
        )
        match = re.search(pattern, gateway_args)
        if not match:
            return

        password, port, username, remote_addr, key_path = match.groups()
        password = password or None
        key_path = key_path or None

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

        server.start()
        self.connect_params['hostname'] = '127.0.0.1'
        self.connect_params['port'] = server.local_bind_port
        self.gateway_server = server

    def local_gateway_clean(self):
        if self.gateway_server:
            self.gateway_server.stop()

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
            pass
