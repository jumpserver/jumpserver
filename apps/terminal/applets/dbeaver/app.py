import time

from pywinauto import Application

from common import wait_pid, BaseApplication


_default_path = r'C:\Program Files\DBeaver\dbeaver-cli.exe'


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
        self.name = '%s-%s-%s' % (self.host, self.db, int(time.time()))
        self.pid = None
        self.app = None

    def _get_exec_params(self):
        driver = getattr(self, 'driver', self.protocol)
        params_string = f'name={self.name}|' \
                        f'driver={driver}|' \
                        f'host={self.host}|' \
                        f'port={self.port}|' \
                        f'database={self.db}|' \
                        f'"user={self.username}"|' \
                        f'password={self.password}|' \
                        f'save=false|' \
                        f'connect=true'
        return params_string

    def _get_mysql_exec_params(self):
        params_string = self._get_exec_params()
        params_string += '|prop.allowPublicKeyRetrieval=true'
        return params_string

    def _get_oracle_exec_params(self):
        if self.privileged:
            self.username = '%s as sysdba' % self.username
        return self._get_exec_params()

    def _get_sqlserver_exec_params(self):
        setattr(self, 'driver', 'mssql_jdbc_ms_new')
        return self._get_exec_params()

    def run(self):
        self.app = Application(backend='uia')

        function = getattr(self, '_get_%s_exec_params' % self.protocol, None)
        if function is None:
            params = self._get_exec_params()
        else:
            params = function()
        self.app.start('%s -con %s' % (self.path, params), wait_for_idle=False)
        self.pid = self.app.process

    def wait(self):
        wait_pid(self.pid)
