import time

import paramiko
from paramiko.ssh_exception import SSHException, NoValidConnectionsError


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=22),
        login_user=dict(type='str', required=False, default='root'),
        login_password=dict(type='str', required=False, no_log=True),
        login_secret_type=dict(type='str', required=False, default='password'),
        login_private_key_path=dict(type='str', required=False, no_log=True),
    )
    return options


class SSHClient:
    def __init__(self, module):
        self.module = module
        self.is_connect = False
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def get_connect_params(self):
        params = {
            'allow_agent': False, 'look_for_keys': False,
            'hostname': self.module.params['login_host'],
            'port': self.module.params['login_port'],
            'username': self.module.params['login_user'],
        }
        secret_type = self.module.params['login_secret_type']
        if secret_type == 'ssh_key':
            params['key_filename'] = self.module.params['login_private_key_path']
        else:
            params['password'] = self.module.params['login_password']
        return params

    def connect(self):
        try:
            self.client.connect(**self.get_connect_params())
        except (SSHException, NoValidConnectionsError) as err:
            err_msg = str(err)
        else:
            self.is_connect = True
            err_msg = ''
        return err_msg

    def execute(self, commands):
        if not self.is_connect:
            self.connect()

        channel = self.client.invoke_shell()
        # 读取首次登陆终端返回的消息
        channel.recv(2048)
        # 网络设备一般登录有延迟，等终端有返回后再执行命令
        delay_time = self.module.params['first_conn_delay_time']
        time.sleep(delay_time)
        err_msg = ''
        try:
            for command in commands:
                channel.send(command + '\n')
                time.sleep(0.3)
        except SSHException as e:
            err_msg = str(e)
        return err_msg
