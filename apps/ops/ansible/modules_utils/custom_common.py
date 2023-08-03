import time

import paramiko


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=22),
        login_user=dict(type='str', required=False, default='root'),
        login_password=dict(type='str', required=False, no_log=True),
        login_secret_type=dict(type='str', required=False, default='password'),
        login_private_key_path=dict(type='str', required=False, no_log=True),
        first_conn_delay_time=dict(type='float', required=False, default=0.5),

        become=dict(type='bool', default=False, required=False),
        become_method=dict(type='str', required=False),
        become_user=dict(type='str', required=False),
        become_password=dict(type='str', required=False, no_log=True),
        become_private_key_path=dict(type='str', required=False, no_log=True),
    )
    return options


class SSHClient:
    def __init__(self, module):
        self.module = module
        self.channel = None
        self.is_connect = False
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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
        remote_user = content.split()[1] if len(content.split()) >= 3 else None
        return remote_user and remote_user == user

    def switch_user(self):
        self._get_channel()
        if not self.module.params['become']:
            return None
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
        i_output, err_msg = self.execute(['whoami'])
        if err_msg:
            return err_msg

        if self._is_match_user(username, i_output):
            err_msg = ''
        else:
            err_msg = su_output
        return err_msg

    def connect(self):
        try:
            self.client.connect(**self.get_connect_params())
            self.is_connect = True
            err_msg = self.switch_user()
        except Exception as err:
            err_msg = str(err)
        return err_msg

    def _get_recv(self, size=1024, encoding='utf-8'):
        output = self.channel.recv(size).decode(encoding)
        return output

    def execute(self, commands):
        if not self.is_connect:
            self.connect()
        output, error_msg = '', ''
        try:
            for command in commands:
                self.channel.send(command + '\n')
                time.sleep(0.3)
                output = self._get_recv()
        except Exception as e:
            error_msg = str(e)
        return output, error_msg

    def __del__(self):
        try:
            self.channel.close()
            self.client.close()
        except:
            pass
