import os
import shutil
import subprocess
import time
from xml.etree import ElementTree
from xml.sax import SAXException

import win32api

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
        if self.tinker_forward:
            self.host = self.tinker_forward.host
            self.port = self.tinker_forward.port

        self.db = self.asset.spec_info.db_name
        self.name = '%s-%s-%s' % (self.host, self.db, int(time.time()))
        self.app_work_path = self.get_app_work_path()
        self.pid = None
        self.app = None

    @staticmethod
    def get_app_work_path():
        win_user_name = win32api.GetUserName()
        return r'C:\Users\%s\AppData\Roaming\DBeaverData' % win_user_name

    @staticmethod
    def _read_config(config_file):
        default_config = {}
        if not os.path.exists(config_file):
            return default_config

        with open(config_file, 'r') as f:
            for line in f.readlines():
                try:
                    config_key, config_value = line.split('=')
                except ValueError:
                    continue
                default_config[config_key] = config_value
        return default_config

    @staticmethod
    def _write_config(config_file, config):
        with open(config_file, 'w')as f:
            for key, value in config.items():
                f.write(f'{key}={value}\n')

    @staticmethod
    def _merge_driver_xml(src_path, dest_path):
        tree1 = ElementTree.parse(dest_path)
        tree2 = ElementTree.parse(src_path)

        for child2 in tree2.getroot():
            found = False
            for child1 in tree1.getroot():
                if child1.tag == child2.tag and child1.attrib == child2.attrib:
                    found = True
                    break
            if not found:
                tree1.getroot().append(child2)
        tree1.write(dest_path)

    def init_driver(self):
        src_driver = os.path.join(os.path.dirname(self.path), 'drivers')
        dest_driver = os.path.join(self.app_work_path, 'drivers')
        if not os.path.exists(dest_driver):
            shutil.copytree(src_driver, dest_driver, dirs_exist_ok=True)

    def init_driver_config(self):
        driver_yml_path = os.path.join(
            self.app_work_path, 'workspace6', '.metadata', '.config',
        )
        driver_yml_file = os.path.join(driver_yml_path, 'drivers.xml')
        try:
            self._merge_driver_xml('./config/drivers.xml', driver_yml_file)
        except (SAXException, FileNotFoundError):
            os.makedirs(driver_yml_path, exist_ok=True)
            shutil.copy('./config/drivers.xml', driver_yml_file)

    def init_other_config(self):
        config_path = os.path.join(
            self.app_work_path, 'workspace6', '.metadata',
            '.plugins', 'org.eclipse.core.runtime', '.settings',
        )
        os.makedirs(config_path, exist_ok=True)
        config_file = os.path.join(config_path, 'org.jkiss.dbeaver.core.prefs')

        config = self._read_config(config_file)
        config['ui.auto.update.check'] = 'false'
        config['sample.database.canceled'] = 'true'
        config['tipOfTheDayInitializer.notFirstRun'] = 'true'
        config['ui.show.tip.of.the.day.on.startup'] = 'false'
        self._write_config(config_file, config)

    def launch(self):
        self.init_driver()
        self.init_driver_config()
        self.init_other_config()

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
        exec_string = '%s -con %s' % (self.path, params)
        ret = subprocess.Popen(exec_string, startupinfo=startupinfo)
        self.pid = ret.pid

    def wait(self):
        wait_pid(self.pid)
