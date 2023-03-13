from pywinauto import Application

from common import wait_pid, BaseApplication


_default_path = r'C:\Program Files\PLSQL Developer 12\plsqldev.exe'


class AppletApplication(BaseApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = _default_path
        self.username = self.account.username
        self.password = self.account.secret
        self.privileged = self.account.privileged
        self.host = self.asset.address
        self.port = self.asset.get_protocol_port(self.protocol)
        self.db = self.asset.spec_info.db_name
        self.pid = None
        self.app = None

    def _get_exec_params(self):
        params_string = f'userid="{self.username}/{self.password}@{self.host}:{self.port}/{self.db}%s"'
        if self.privileged:
            params_string = params_string % ' as sysdba'
        else:
            params_string = params_string % ''
        return params_string

    def run(self):
        self.app = Application(backend='uia')
        params = self._get_exec_params()
        self.app.start(r'%s %s' % (self.path, params), wait_for_idle=False)
        self.pid = self.app.process

    def wait(self):
        wait_pid(self.pid)
