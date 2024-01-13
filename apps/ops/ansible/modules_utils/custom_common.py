import re
import time

import paramiko
from sshtunnel import SSHTunnelForwarder

from packaging import version

if version.parse(paramiko.__version__) > version.parse("2.8.1"):
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
    paramiko.transport.Transport._preferred_pubkeys = _preferred_pubkeys


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=22),
        login_user=dict(type='str', required=False, default='root'),
        login_password=dict(type='str', required=False, no_log=True),
        login_secret_type=dict(type='str', required=False, default='password'),
        login_private_key_path=dict(type='str', required=False, no_log=True),
        first_conn_delay_time=dict(type='float', required=False, default=0.5),
        gateway_args=dict(type='str', required=False, default=''),

        become=dict(type='bool', default=False, required=False),
        become_method=dict(type='str', required=False),
        become_user=dict(type='str', required=False),
        become_password=dict(type='str', required=False, no_log=True),
        become_private_key_path=dict(type='str', required=False, no_log=True),
    )
    return options


class SSHClient:
    TIMEOUT = 20
    SLEEP_INTERVAL = 2
    COMPLETE_FLAG = 'complete'

    def __init__(self, module):
        self.module = module
        self.channel = None
        self.is_connect = False
        self.gateway_server = None
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect_params = self.get_connect_params()

    def get_connect_params(self):
        params = {
            'allow_agent': False, 'look_for_keys': False,
            'hostname': self.module.params['login_host'],
            'port': self.module.params['login_port'],
            'key_filename': self.module.params['login_private_key_path'] or None
        }
        if self.module.params['become']:
            params['username'] = self.module.params['become_user']
            params['password'] = self.module.params['become_password']
            params['key_filename'] = self.module.params['become_private_key_path'] or None
        else:
            params['username'] = self.module.params['login_user']
            params['password'] = self.module.params['login_password']
            params['key_filename'] = self.module.params['login_private_key_path'] or None
        return params

    def _get_channel(self):
        self.channel = self.client.invoke_shell()
        # 读取首次登陆终端返回的消息
        self.channel.recv(2048)
        # 网络设备一般登录有延迟，等终端有返回后再执行命令
        delay_time = self.module.params['first_conn_delay_time']
        time.sleep(delay_time)

    @staticmethod
    def _is_match_user(user, content):
        # 正常命令切割后是[命令，用户名，交互前缀]
        content_list = content.split() if len(content.split()) >= 3 else None
        return content_list and user in content_list

    def switch_user(self):
        self._get_channel()
        if not self.module.params['become']:
            return
        method = self.module.params['become_method']
        username = self.module.params['login_user']
        if method == 'sudo':
            switch_method = 'sudo su -'
            password = self.module.params['become_password']
        elif method == 'su':
            switch_method = 'su -'
            password = self.module.params['login_password']
        else:
            self.module.fail_json(msg='Become method %s not support' % method)
            return
        commands = [f'{switch_method} {username}', password]
        su_output, err_msg = self.execute(commands)
        if err_msg:
            return err_msg
        i_output, err_msg = self.execute(
            [f'whoami && echo "{self.COMPLETE_FLAG}"'],
            validate_output=True
        )
        if err_msg:
            return err_msg

        if self._is_match_user(username, i_output):
            err_msg = ''
        else:
            err_msg = su_output
        return err_msg

    def local_gateway_prepare(self):
        gateway_args = self.module.params['gateway_args'] or ''
        pattern = r"(?:sshpass -p ([\w@]+))?\s*ssh -o Port=(\d+)\s+-o StrictHostKeyChecking=no\s+([\w@]+)@([" \
                  r"\d.]+)\s+-W %h:%p -q(?: -i (.+))?'"
        match = re.search(pattern, gateway_args)

        if not match:
            return

        password, port, username, address, private_key_path = match.groups()
        password = password if password else None
        private_key_path = private_key_path if private_key_path else None
        remote_hostname = self.module.params['login_host']
        remote_port = self.module.params['login_port']

        server = SSHTunnelForwarder(
            (address, int(port)),
            ssh_username=username,
            ssh_password=password,
            ssh_pkey=private_key_path,
            remote_bind_address=(remote_hostname, remote_port)
        )

        server.start()
        self.connect_params['hostname'] = '127.0.0.1'
        self.connect_params['port'] = server.local_bind_port
        self.gateway_server = server

    def local_gateway_clean(self):
        gateway_server = self.gateway_server
        if not gateway_server:
            return
        try:
            gateway_server.stop()
        except Exception:
            pass

    def before_runner_start(self):
        self.local_gateway_prepare()

    def after_runner_end(self):
        self.local_gateway_clean()

    def connect(self):
        try:
            self.before_runner_start()
            self.client.connect(**self.connect_params)
            self.is_connect = True
            err_msg = self.switch_user()
            self.after_runner_end()
        except Exception as err:
            err_msg = str(err)
        return err_msg

    def _get_recv(self, size=1024, encoding='utf-8'):
        output = self.channel.recv(size).decode(encoding)
        return output

    def execute(self, commands, validate_output=False):
        if not self.is_connect:
            self.connect()
        output, error_msg = '', ''
        try:
            for command in commands:
                self.channel.send(command + '\n')
                if not validate_output:
                    time.sleep(self.SLEEP_INTERVAL)
                    output += self._get_recv()
                    continue
                start_time = time.time()
                while self.COMPLETE_FLAG not in output:
                    if time.time() - start_time > self.TIMEOUT:
                        error_msg = output
                        print("切换用户操作超时，跳出循环。")
                        break
                    time.sleep(self.SLEEP_INTERVAL)
                    received_output = self._get_recv().replace(f'"{self.COMPLETE_FLAG}"', '')
                    output += received_output
        except Exception as e:
            error_msg = str(e)
        return output, error_msg

    def __del__(self):
        try:
            self.channel.close()
            self.client.close()
        except Exception:
            pass
