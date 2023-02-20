import os
import time
import win32api
import shutil
import subprocess

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

    def launch(self):
        win_user_name = win32api.GetUserName()
        src_driver = os.path.join(os.path.dirname(self.path), 'drivers')
        dest_driver = r'C:\Users\%s\AppData\Roaming\DBeaverData\drivers' % win_user_name
        if not os.path.exists(dest_driver):
            shutil.copytree(src_driver, dest_driver, dirs_exist_ok=True)

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
        self.launch()

        function = getattr(self, '_get_%s_exec_params' % self.protocol, None)
        if function is None:
            params = self._get_exec_params()
        else:
            params = function()

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        ret = subprocess.Popen([self.path, '-con', params], startupinfo=startupinfo)
        self.pid = ret.pid

    def wait(self):
        wait_pid(self.pid)
