import sys
import time

if sys.platform == 'win32':
    import winreg
    import win32api

    from pywinauto import Application
    from pywinauto.controls.uia_controls import (
        EditWrapper, ComboBoxWrapper, ButtonWrapper
    )
from common import wait_pid, BaseApplication


_default_path = r'C:\Program Files\PremiumSoft\Navicat Premium 16\navicat.exe'


class AppletApplication(BaseApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = _default_path
        self.username = self.account.username
        self.password = self.account.secret
        self.privileged = self.account.privileged
        self.host = self.asset.address
        self.port = self.asset.get_protocol_port(self.protocol)
        self.db = self.asset.specific.db_name
        self.name = '%s-%s' % (self.host, self.db)
        self.pid = None
        self.app = None

    def clean_up(self):
        protocol_mapping = {
            'mariadb': 'NavicatMARIADB', 'mongodb': 'NavicatMONGODB',
            'mysql': 'Navicat', 'oracle': 'NavicatORA',
            'sqlserver': 'NavicatMSSQL', 'postgresql': 'NavicatPG'
        }
        protocol_display = protocol_mapping.get(self.protocol, 'mysql')
        sub_key = r'Software\PremiumSoft\%s\Servers' % protocol_display
        try:
            win32api.RegDeleteTree(winreg.HKEY_CURRENT_USER, sub_key)
        except Exception as err:
            print('Error: %s' % err)

    @staticmethod
    def launch():
        sub_key = r'Software\PremiumSoft\NavicatPremium'
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, sub_key)
            # 禁止弹出欢迎页面
            winreg.SetValueEx(key, 'AlreadyShowNavicatV16WelcomeScreen', 0, winreg.REG_DWORD, 1)
            # 禁止开启自动检查更新
            winreg.SetValueEx(key, 'AutoCheckUpdate', 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, 'ShareUsageData', 0, winreg.REG_DWORD, 0)
        except Exception as err:
            print('Launch error: %s' % err)

    def _fill_to_mysql(self, app, menu, protocol_display='MySQL'):
        menu.item_by_path('File->New Connection->%s' % protocol_display).click_input()
        conn_window = app.window(best_match='Dialog').child_window(title_re='New Connection')

        name_ele = conn_window.child_window(best_match='Edit5')
        EditWrapper(name_ele.element_info).set_edit_text(self.name)

        host_ele = conn_window.child_window(best_match='Edit4')
        EditWrapper(host_ele.element_info).set_edit_text(self.host)

        port_ele = conn_window.child_window(best_match='Edit2')
        EditWrapper(port_ele.element_info).set_edit_text(self.port)

        username_ele = conn_window.child_window(best_match='Edit1')
        EditWrapper(username_ele.element_info).set_edit_text(self.username)

        password_ele = conn_window.child_window(best_match='Edit3')
        EditWrapper(password_ele.element_info).set_edit_text(self.password)

    def _fill_to_mariadb(self, app, menu):
        self._fill_to_mysql(app, menu, 'MariaDB')

    def _fill_to_mongodb(self, app, menu):
        menu.item_by_path('File->New Connection->MongoDB').click_input()
        conn_window = app.window(best_match='Dialog').child_window(title_re='New Connection')

        auth_type_ele = conn_window.child_window(best_match='ComboBox2')
        ComboBoxWrapper(auth_type_ele.element_info).select('Password')

        name_ele = conn_window.child_window(best_match='Edit5')
        EditWrapper(name_ele.element_info).set_edit_text(self.name)

        host_ele = conn_window.child_window(best_match='Edit4')
        EditWrapper(host_ele.element_info).set_edit_text(self.host)

        port_ele = conn_window.child_window(best_match='Edit2')
        EditWrapper(port_ele.element_info).set_edit_text(self.port)

        db_ele = conn_window.child_window(best_match='Edit6')
        EditWrapper(db_ele.element_info).set_edit_text(self.db)

        username_ele = conn_window.child_window(best_match='Edit1')
        EditWrapper(username_ele.element_info).set_edit_text(self.username)

        password_ele = conn_window.child_window(best_match='Edit3')
        EditWrapper(password_ele.element_info).set_edit_text(self.password)

    def _fill_to_postgresql(self, app, menu):
        menu.item_by_path('File->New Connection->PostgreSQL').click_input()
        conn_window = app.window(best_match='Dialog').child_window(title_re='New Connection')

        name_ele = conn_window.child_window(best_match='Edit6')
        EditWrapper(name_ele.element_info).set_edit_text(self.name)

        host_ele = conn_window.child_window(best_match='Edit5')
        EditWrapper(host_ele.element_info).set_edit_text(self.host)

        port_ele = conn_window.child_window(best_match='Edit2')
        EditWrapper(port_ele.element_info).set_edit_text(self.port)

        db_ele = conn_window.child_window(best_match='Edit4')
        EditWrapper(db_ele.element_info).set_edit_text(self.db)

        username_ele = conn_window.child_window(best_match='Edit1')
        EditWrapper(username_ele.element_info).set_edit_text(self.username)

        password_ele = conn_window.child_window(best_match='Edit3')
        EditWrapper(password_ele.element_info).set_edit_text(self.password)

    def _fill_to_sqlserver(self, app, menu):
        menu.item_by_path('File->New Connection->SQL Server').click_input()
        conn_window = app.window(best_match='Dialog').child_window(title_re='New Connection')

        name_ele = conn_window.child_window(best_match='Edit5')
        EditWrapper(name_ele.element_info).set_edit_text(self.name)

        host_ele = conn_window.child_window(best_match='Edit4')
        EditWrapper(host_ele.element_info).set_edit_text('%s,%s' % (self.host, self.port))

        db_ele = conn_window.child_window(best_match='Edit3')
        EditWrapper(db_ele.element_info).set_edit_text(self.db)

        username_ele = conn_window.child_window(best_match='Edit6')
        EditWrapper(username_ele.element_info).set_edit_text(self.username)

        password_ele = conn_window.child_window(best_match='Edit2')
        EditWrapper(password_ele.element_info).set_edit_text(self.password)

    def _fill_to_oracle(self, app, menu):
        menu.item_by_path('File->New Connection->Oracle').click_input()
        conn_window = app.window(best_match='Dialog').child_window(title_re='New Connection')

        name_ele = conn_window.child_window(best_match='Edit6')
        EditWrapper(name_ele.element_info).set_edit_text(self.name)

        host_ele = conn_window.child_window(best_match='Edit5')
        EditWrapper(host_ele.element_info).set_edit_text(self.host)

        port_ele = conn_window.child_window(best_match='Edit3')
        EditWrapper(port_ele.element_info).set_edit_text(self.port)

        db_ele = conn_window.child_window(best_match='Edit2')
        EditWrapper(db_ele.element_info).set_edit_text(self.db)

        username_ele = conn_window.child_window(best_match='Edit')
        EditWrapper(username_ele.element_info).set_edit_text(self.username)

        password_ele = conn_window.child_window(best_match='Edit4')
        EditWrapper(password_ele.element_info).set_edit_text(self.password)

        if self.privileged:
            conn_window.child_window(best_match='Advanced', control_type='TabItem').click_input()
            role_ele = conn_window.child_window(best_match='ComboBox2')
            ComboBoxWrapper(role_ele.element_info).select('SYSDBA')

    def run(self):
        self.launch()
        app = Application(backend='uia')
        app.start(self.path)
        self.pid = app.process

        # 检测是否为试用版本
        try:
            trial_btn = app.top_window().child_window(
                best_match='Trial', control_type='Button'
            )
            ButtonWrapper(trial_btn.element_info).click()
            time.sleep(0.5)
        except Exception:
            pass

        menubar = app.window(best_match='Navicat Premium', control_type='Window') \
            .child_window(best_match='Menu', control_type='MenuBar')

        file = menubar.child_window(best_match='File', control_type='MenuItem')
        file.click_input()
        menubar.item_by_path('File->New Connection').click_input()

        # 根据协议选择动作
        action = getattr(self, '_fill_to_%s' % self.protocol, None)
        if action is None:
            raise ValueError('This protocol is not supported: %s' % self.protocol)
        action(app, menubar)

        conn_window = app.window(best_match='Dialog').child_window(title_re='New Connection')
        ok_btn = conn_window.child_window(best_match='OK', control_type='Button')
        ok_btn.click()

        file.click_input()
        menubar.item_by_path('File->Open Connection').click_input()
        self.app = app

    def wait(self):
        try:
            wait_pid(self.pid)
        except Exception:
            pass
        finally:
            self.clean_up()
