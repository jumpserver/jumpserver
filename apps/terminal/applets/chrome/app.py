import time
from enum import Enum
from subprocess import CREATE_NO_WINDOW

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from code_dialog import CodeDialog
from common import (Asset, User, Account, Platform, Step)
from common import (BaseApplication)
from common import (notify_err_message, block_input, unblock_input)


class Command(Enum):
    TYPE = 'type'
    CLICK = 'click'
    OPEN = 'open'
    CODE = 'code'


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


def execute_action(driver: webdriver.Chrome, step: StepAction) -> bool:
    try:
        return step.execute(driver)
    except Exception as e:
        print(e)
        notify_err_message(str(e))
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
                    val = val.replace("{USERNAME}", self.account.username)
                    val = val.replace("{SECRET}", self.account.secret)
                item.value = val
                self._steps.append(item)

    def _default_custom_steps(self, spec_info) -> list:
        account = self.account
        default_steps = [
            Step({
                "step": 1,
                "value": account.username,
                "target": spec_info.username_selector,
                "command": "type"
            }),
            Step({
                "step": 2,
                "value": account.secret,
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
        return default_steps

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


def default_chrome_driver_options():
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    # 禁用 扩展
    options.add_argument("--disable-extensions")
    # 禁用开发者工具
    options.add_argument("--disable-dev-tools")
    # 禁用 密码管理器弹窗
    prefs = {"credentials_enable_service": False,
             "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    return options


class AppletApplication(BaseApplication):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = None
        self.app = WebAPP(app_name=self.app_name, user=self.user,
                          account=self.account, asset=self.asset, platform=self.platform)
        self._chrome_options = default_chrome_driver_options()

    def run(self):
        service = Service()
        #  driver 的 console 终端框不显示
        service.creationflags = CREATE_NO_WINDOW
        self.driver = webdriver.Chrome(options=self._chrome_options, service=service)
        self.driver.implicitly_wait(10)
        if self.app.asset.address != "":
            self.driver.get(self.app.asset.address)
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
