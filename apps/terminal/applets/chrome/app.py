import os
import tempfile
import time
from enum import Enum
from subprocess import CREATE_NO_WINDOW

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from code_dialog import CodeDialog, wrapper_progress_bar
from common import (Asset, User, Account, Platform, Step)
from common import (BaseApplication)
from common import (notify_err_message, block_input, unblock_input)


class Command(Enum):
    TYPE = 'type'
    CLICK = 'click'
    OPEN = 'open'
    CODE = 'code'
    SELECT_FRAME = 'select_frame'
    SLEEP = 'sleep'


def _execute_type(ele: WebElement, value: str):
    ele.send_keys(value)


def _execute_click(ele: WebElement, value: str):
    ele.click()


commands_func_maps = {
    Command.CLICK: _execute_click,
    Command.TYPE: _execute_type,
    Command.OPEN: _execute_type,
}


class StepAction:
    methods_map = {
        "NAME": By.NAME,
        "ID": By.ID,
        "CLASS_NAME": By.CLASS_NAME,
        "CSS_SELECTOR": By.CSS_SELECTOR,
        "CSS": By.CSS_SELECTOR,
        "XPATH": By.XPATH
    }

    def __init__(self, target='', value='', command=Command.TYPE, **kwargs):
        self.target = target
        self.value = value
        self.command = command

    def execute(self, driver: webdriver.Chrome) -> bool:
        if not self.target:
            return True
        if self.command == 'select_frame':
            self._switch_iframe(driver, self.target)
            return True
        elif self.command == 'sleep':
            self._sleep(driver, self.target)
            return True
        target_name, target_value = self.target.split("=", 1)
        by_name = self.methods_map.get(target_name.upper(), By.NAME)
        ele = driver.find_element(by=by_name, value=target_value)
        if not ele:
            return False
        if self.command == 'type':
            ele.send_keys(self.value)
        elif self.command in ['click', 'button']:
            ele.click()
        elif self.command in ['open']:
            driver.get(self.value)
        elif self.command == 'code':
            unblock_input()
            code_string = CodeDialog(title="Code Dialog", label="Code").wait_string()
            block_input()
            ele.send_keys(code_string)
        return True

    def _execute_command_type(self, ele, value):
        ele.send_keys(value)

    def _switch_iframe(self, driver: webdriver.Chrome, target: str):
        """
        driver: webdriver.Chrome
        target: str
        target support three format str below:
            index=1: switch to frame by index, if index < 0, switch to default frame
            id=xxx: switch to frame by id
            name=xxx: switch to frame by name
        """
        target_name, target_value = target.split("=", 1)
        if target_name == 'id':
            driver.switch_to.frame(target_value)
        elif target_name == 'index':
            index = int(target_value)
            if index < 0:
                driver.switch_to.default_content()
            else:
                driver.switch_to.frame(index)
        elif target_name == 'name':
            driver.switch_to.frame(target_value)
        else:
            driver.switch_to.frame(target)

    def _sleep(self, driver: webdriver.Chrome, target: str):
        try:
            sleep_time = int(target)
        except Exception as e:
            # at least sleep 1 second
            sleep_time = 1
        time.sleep(sleep_time)


def execute_action(driver: webdriver.Chrome, step: StepAction) -> bool:
    try:
        return step.execute(driver)
    except Exception as e:
        print(e)
        return False


class WebAPP(object):

    def __init__(self, app_name: str = '', user: User = None, asset: Asset = None,
                 account: Account = None, platform: Platform = None, **kwargs):
        self.app_name = app_name
        self.user = user
        self.asset = asset
        self.account = account
        self.platform = platform
        self._steps = list()
        # 确保 account_username 和 account_secret 不为 None
        self._account_username = account.username if account.username else ''
        self._account_secret = account.secret if account.secret else ''

        # 如果是匿名账号，account_username 和 account_secret 为空
        if account.username == "@ANON":
            self._account_username = ''
            self._account_secret = ''

        extra_data = self.asset.spec_info
        autofill_type = extra_data.autofill
        if not autofill_type:
            protocol_setting = self.platform.get_protocol_setting("http")
            if not protocol_setting:
                print("No protocol setting found")
                return
            extra_data = protocol_setting
            autofill_type = extra_data.autofill
        if autofill_type == "basic":
            self._steps = self._default_custom_steps(extra_data)
        elif autofill_type == "script":
            script_list = extra_data.script
            steps = sorted(script_list, key=lambda step_item: step_item.step)
            for item in steps:
                val = item.value
                if val:
                    val = val.replace("{USERNAME}", self._account_username)
                    val = val.replace("{SECRET}", self._account_secret)
                item.value = val
                self._steps.append(item)

    def _default_custom_steps(self, spec_info) -> list:
        return [
            Step({
                "step": 1,
                "value": self._account_username,
                "target": spec_info.username_selector,
                "command": "type"
            }),
            Step({
                "step": 2,
                "value": self._account_secret,
                "target": spec_info.password_selector,
                "command": "type"
            }),
            Step({
                "step": 3,
                "value": "",
                "target": spec_info.submit_selector,
                "command": "click"
            })
        ]

    def execute(self, driver: webdriver.Chrome) -> bool:
        if not self.asset.address:
            return True

        for step in self._steps:
            action = StepAction(target=step.target, value=step.value,
                                command=step.command)
            ret = execute_action(driver, action)
            if not ret:
                unblock_input()
                notify_err_message(f"执行失败: target: {action.target} command: {action.command}")
                block_input()
                return False
        return True


def load_extensions():
    extensions_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extensions')
    extension_names = os.listdir(extensions_root)
    extension_paths = [os.path.join(extensions_root, name) for name in extension_names]
    return extension_paths


def default_chrome_driver_options():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    # 忽略证书错误相关
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--allow-running-insecure-content')

    # 禁用开发者工具
    options.add_argument("--disable-dev-tools")
    # 禁用 密码管理器弹窗
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    return options


class AppletApplication(BaseApplication):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = None
        self.app = WebAPP(app_name=self.app_name, user=self.user,
                          account=self.account, asset=self.asset, platform=self.platform)
        self._tmp_user_dir = tempfile.TemporaryDirectory()
        self._chrome_options = default_chrome_driver_options()
        self._chrome_options.add_argument("--app={}".format(self.asset.address))
        self._chrome_options.add_argument("--user-data-dir={}".format(self._tmp_user_dir.name))
        protocol_setting = self.platform.get_protocol_setting(self.protocol)
        if protocol_setting and protocol_setting.safe_mode:
            # 加载 extensions
            extension_paths = load_extensions()
            for extension_path in extension_paths:
                self._chrome_options.add_argument('--load-extension={}'.format(extension_path))

    @wrapper_progress_bar
    def run(self):
        service = Service()
        #  driver 的 console 终端框不显示
        service.creationflags = CREATE_NO_WINDOW
        self.driver = webdriver.Chrome(options=self._chrome_options, service=service)
        self.driver.implicitly_wait(10)
        if self.app.asset.address != "":
            ok = self.app.execute(self.driver)
            if not ok:
                print("执行失败")
        self.driver.maximize_window()

    def wait(self):
        disconnected_msg = "Unable to evaluate script: disconnected: not connected to DevTools\n"
        closed_msg = "Unable to evaluate script: no such window: target window already closed"

        while True:
            time.sleep(5)
            logs = self.driver.get_log('driver')
            if len(logs) == 0:
                continue
            ret = logs[-1]
            if isinstance(ret, dict):
                message = ret.get('message', '')
                if disconnected_msg in message or closed_msg in message:
                    break
                print("ret: ", ret)
        self.close()

    def close(self):
        if self.driver:
            try:
                # quit 退出全部打开的窗口
                self.driver.quit()
            except Exception as e:
                print(e)
        try:
            self._tmp_user_dir.cleanup()
        except Exception as e:
            print(e)
